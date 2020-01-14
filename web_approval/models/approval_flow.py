# -*- coding: utf-8 -*-
import inspect
import json
import sys
import logging
import types
from lxml import etree

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

APPROVAL_TYPE = [('group', u'组'), ('user', u'用户'), ('job', u'岗位'), ('leader', u'直属领导'), ('department_head', u'部门领导')]
WAIT_APPROVAL_STATE = [('active', u'草稿'), ('running', u'正在审批'), ('complete', u'完成')]
RECORD_STATE = [('active', u'活动'), ('complete', u'完成'), ('pause', u'暂停'), ('cancel', u'取消')]


class ApprovalFlow(models.Model):
    _name = 'approval.flow'
    _inherit = ['mail.thread']
    _description = '审批流程'

    def _compute_domain(self):
        all_cls = inspect.getmembers(sys.modules[__name__], inspect.isclass)
        odoo_cls = [getattr(cls[1], '_name') for cls in all_cls if cls[1].__bases__[0].__name__ == 'Model']  # 排除当前的对象
        odoo_cls += [model.model for model in self.env['ir.model'].search([('transient', '=', True)])]  # 排除临时对象

        return [('model', 'not in', odoo_cls)]

    # 基本字段
    name = fields.Char('名称', required=1, track_visibility='onchange')
    model_id = fields.Many2one('ir.model', '模型', domain=_compute_domain, index=1, required=0,
                               track_visibility='onchange', ondelete="set null")

    @api.onchange('model_id')
    def onchange_model_id(self):
        for rec in self:
            model_state_domain = [('id', '=', False)]
            model_button_domain = [('id', '=', False)]
            if rec.model_id:
                model_state_ids = self.env['ps.model.state.filed.value'].search([
                    ('model_id', '=', rec.model_id.id), ('state_filed_name', '=', 'state')]).ids
                model_state_domain = [('id', 'in', model_state_ids)]
                model_button_ids = self.env['ps.model.button.value'].search([
                    ('model_id', '=', rec.model_id.id)]).ids
                model_button_domain = [('id', 'in', model_button_ids)]
            return {'domain':
                    {
                        'model_state_filed_value_id': model_state_domain,
                        'model_button_value_ids': model_button_domain
                    }
            }

    model_state_filed_value_id = fields.Many2one('ps.model.state.filed.value', string='模型状态值')
    model_button_value_ids = fields.Many2many('ps.model.button.value', string='模型按钮值')
    condition = fields.Char('条件', help='请遵循odoo的domain的写法，如：[("field_name", "=", value)]', track_visibility='onchange')
    company_ids = fields.Many2many('res.company', 'approval_flow_company_rel', 'flow_id', 'company_id', '适用公司',
                                   default=lambda self: [self.env.user.company_id.id], track_visibility='onchange')
    accept_template = fields.Text('同意模板')
    refuse_template = fields.Text('拒绝模板')
    active = fields.Boolean('有效', default=True)

    node_ids = fields.One2many('approval.flow.node', 'flow_id', u'流程节点')
    action_ids = fields.One2many('approval.flow.node.action', 'flow_id', u'节点动作')

    # 执行方法限制
    approval_can_run = fields.Char('审批后运行', help='审批流程完成后才能执行的功能，比如审核等，用英文逗号间隔', track_visibility='onchange')
    approval_cannot_run = fields.Char(string='审批完成后不允许执行的方法', help='审批流程完成后不能能执行的功能，比如修改、删除等，用英文逗号间隔',
                                      track_visibility='onchange')

    # 动作回调
    completed_run = fields.Char('完成后自动运行', help='审批流程完成后自动执行的函数，用英文逗号间隔', track_visibility='onchange')
    commit_run = fields.Char('送审自动运行', help='审批流程完成后自动执行的函数，用英文逗号间隔', track_visibility='onchange')
    cancel_run = fields.Char('取消审批自动运行', help='审批流程完成后自动执行的函数，用英文逗号间隔', track_visibility='onchange')

    # 完成后抄送
    complete_copy_for_type = fields.Selection([('user', '用户'), ('job', '岗位')], string='完成后挱送类型',
                                              track_visibility='onchange')
    complete_copy_for_only_document_company = fields.Boolean('仅抄送单据公司', default=False, track_visibility='onchange')
    complete_copy_for_user_ids = fields.Many2many('res.users', 'approval_flow_complete_copy_user_rel', 'flow_id',
                                                  'user_id', '抄送用户', track_visibility='onchange')
    complete_copy_for_job_ids = fields.Many2many('hr.job', 'approval_flow_complete_copy_job_rel', 'flow_id', 'job_id',
                                                 '抄送岗位', track_visibility='onchange')

    def check_condition(self, condition):
        try:
            self.env[self.model_id.model].search(eval(condition))
        except Exception as _:
            raise ValidationError(u"错误的条件表达式：'%s'！" % condition)

    @api.constrains('approval_can_run', 'approval_cannot_run', 'completed_run', 'commit_run', 'cancel_run', 'condition',
                    'model_id', 'active', 'company_ids')
    def check_validity(self):
        for flow in self:
            # 校验model_id是否具有company_id字段
            model = self.env[self.model_id.model]
            if getattr(model, 'company_id', False) is False:
                raise ValidationError(u'模型%s没有company_id字段' % self.model_id.model)

            # 校验回调函数
            flow.check_methods_exist(flow.approval_can_run)
            flow.check_methods_exist(flow.approval_cannot_run, ['write', 'unlink'])
            flow.check_methods_exist(flow.completed_run)
            flow.check_methods_exist(flow.commit_run)
            flow.check_methods_exist(flow.cancel_run)

            # 校验条件
            if flow.condition:
                self.check_condition(flow.condition)
            # 校验相同公司相同模型是否存在已生效的审批流程
            records = self.search([('model_id', '=', flow.model_id.id), ('company_ids', 'in', flow.company_ids.ids), (
                'active', '=', True), ('id', '!=', flow.id)])
            if records:
                company_display_name = ''
                for record in records:
                    for company in flow.company_ids:
                        if company in record.company_ids:
                            company_display_name += '【模型--' + flow.model_id.display_name + '+公司--' + company.display_name + '】'
                raise ValidationError(_("'%s'的组合下存在已生效的审批流程，如仍需保存，请将该流程置为无效" % (company_display_name)))

    @api.model
    def create(self, vals):
        if not vals.get('node_ids'):
            vals['node_ids'] = []

        vals['node_ids'].append((0, False, {'name': '开始', 'node_id': self.env.ref('web_approval.start_node').id}))
        vals['node_ids'].append((0, False, {'name': '结束', 'node_id': self.env.ref('web_approval.end_node').id}))

        # 删除回调方法的空格
        for method in ['approval_can_run', 'approval_cannot_run', 'completed_run', 'commit_run', 'cancel_run']:
            self.delete_method_blank(vals, method)

        if vals['condition']:
            vals['condition'] = vals['condition'].replace('true', 'True').replace('false', 'False')
        res = super(ApprovalFlow, self).create(vals)

        # 设置button的黑名单
        for model_button_id in res.model_button_value_ids:
            model_button_id.is_blacklist = True
        return res

    @api.multi
    def write(self, vals):
        if vals.get('model_button_value_ids'):  # 如果修改了button的黑名单
            # 1.移除原来的黑名单中的button
            for rec in self.model_button_value_ids:
                rec.is_blacklist = False
        # 删除回调方法的空格
        for method in ['approval_can_run', 'approval_cannot_run', 'completed_run', 'commit_run', 'cancel_run']:
            self.delete_method_blank(vals, method)

        if vals.get('condition'):
            vals['condition'] = vals['condition'].replace('true', 'True').replace('false', 'False')
        # 如果单据在审批过程中则对应的审批流不允许修改
        for line in self:
            records = self.env['record.approval.state'].sudo().search([('model', '=', line.model_id.model)])
            if records:
                for record in records:
                    if record.approval_state in ['pause', 'active']:
                        raise ValidationError(_("该审批流有单据在审批过程中,不允许修改"))

        # 流程设置完毕，需要升级当前模块
        current_module = self.env['ir.module.module'].search([('name', '=', 'web_approval')])
        current_module.button_immediate_upgrade()
        self.env['ir.ui.view'].sudo().fields_view_get()
        res = super(ApprovalFlow, self).write(vals)
        # 2.再次设置黑名单中的button
        for model_button_id in self.model_button_value_ids:
            model_button_id.is_blacklist = True
        return res

    def action_reload_current_page(self):
        """
        实现一次当前页面的刷新
        :return:
        """
        current_module = self.env['ir.module.module'].search([('name', '=', 'web_approval')])
        current_module.button_immediate_upgrade()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def unlink(self):
        """
        如果单据在审批过程中则对应的审批流不允许删除
        :return:
        """
        # 移除原来的黑名单中的button
        for rec in self.model_button_value_ids:
            rec.is_blacklist = False
        for line in self:
            records = self.env['record.approval.state'].sudo().search([('model', '=', line.model_id.model)])
            if records:
                for record in records:
                    if record.approval_state in ['pause', 'active']:
                        raise ValidationError(_("该审批流有单据在审批过程中,不允许删除"))
            records.filtered(lambda r: not r.flow_id).sudo().unlink()
        return super(ApprovalFlow, self).unlink()

    @staticmethod
    def delete_method_blank(vals, method_name):
        if vals.get(method_name, False):
            vals[method_name] = ','.join([f.strip() for f in vals[method_name].split(',')])

    def check_methods_exist(self, string_methods, exist_methods=None):
        if not string_methods:
            return

        string_methods = list(map(lambda x: x.strip(), string_methods.split(',')))

        model = self.env[self.model_id.model]
        methods = []
        for key in dir(model):
            try:
                value = getattr(model, key)
                if isinstance(value, types.MethodType):
                    methods.append(key)
            except Exception as e:
                continue

        if not exist_methods:
            exist_methods = []

        methods += exist_methods

        for f in string_methods:
            if f not in methods:
                raise ValidationError(u"'%s'不存在方法：'%s'" % (self.model_id.name, f))

    @api.model
    def get_diagram_data(self, res_id):
        approval_flow = self.browse(res_id)

        def get_category(node):
            category = ''
            if node.node_id.is_start:
                category = 'Start'

            if node.node_id.is_end:
                category = 'End'

            return category

        nodes = [{
            'id': node.id,
            'text': node.name,
            'key': str(node.id),
            'category': get_category(node)
        } for node in approval_flow.node_ids]
        actions = [{
            'id': action.id,
            # 'action_type': action.action_type,
            'condition': action.condition,
            'from': str(action.source_node_id.id),
            'to': str(action.target_node_id.id),
        } for action in approval_flow.action_ids]

        return {
            'nodes': nodes,
            'actions': actions,
            'name': approval_flow.name
        }


class ApprovalNode(models.Model):
    _name = 'approval.node'
    _inherit = ['mail.thread']
    _description = '审批节点'

    name = fields.Char(u'名称', required=1, track_visibility='onchange')
    is_start = fields.Boolean(u'流程开始')
    is_end = fields.Boolean(u'流程结束')
    type = fields.Selection(APPROVAL_TYPE, u'审批类型', required=0, track_visibility='onchange')

    # 组审批
    groups_id = fields.Many2one('res.groups', u'节点执行组', track_visibility='onchange')
    is_all_approval = fields.Boolean(u'需全组审批', default=False, track_visibility='onchange')
    only_document_company = fields.Boolean(u'仅单据公司', default=False, track_visibility='onchange')

    # 用户审批
    user_ids = fields.Many2many('res.users', 'approval_flow_node_user_rel', 'approval_flow_node_id', 'user_id', u'用户',
                                track_visibility='onchange')
    user_only_document_company = fields.Boolean(u'仅单据公司', default=False, track_visibility='onchange')
    user_is_all_approval = fields.Boolean(u'需所有用户审批', default=False, track_visibility='onchange')

    # 岗位审批
    job_ids = fields.Many2many('hr.job', 'approval_flow_node_job_rel', 'approval_flow_node_id', 'job_id', u'岗位',
                               track_visibility='onchange')
    job_only_document_company = fields.Boolean(u'仅单据公司', default=False, track_visibility='onchange')
    job_is_all_approval = fields.Boolean(u'需岗位所有成员审批', default=False, track_visibility='onchange')

    # 直属领导审批
    need_parent_parent = fields.Boolean(u'需直属领导的上级审批', help=u'领导审批完成后，是否需要领导的上级审批。', track_visibility='onchange')

    # 部门领导审批
    need_department_parent = fields.Boolean(u'需部门领导的上级审批', help=u'领导审批完成后，是否需要领导的上级审批。', track_visibility='onchange')

    duration = fields.Integer(u'审批时效', default=0, track_visibility='onchange')
    allow_before_increase = fields.Boolean(u'允许前加签', default=False, track_visibility='onchange')
    allow_after_increase = fields.Boolean(u'允许后加签', default=False, track_visibility='onchange')
    allow_turn_to = fields.Boolean(u'允许代签', default=True, track_visibility='onchange')

    # 结节状态为完成时自动运行
    complete_run = fields.Char(u'节点完成自动运行', help=u'结节状态为完成时自动执行的函数，用英文逗号间隔', track_visibility='onchange')


class ApprovalFlowNode(models.Model):
    _name = 'approval.flow.node'
    _description = '流程节点'

    name = fields.Char('名称', required=1)

    flow_id = fields.Many2one('approval.flow', u'流程', ondelete='cascade')
    node_id = fields.Many2one('approval.node', '审批节点', required=1)

    type = fields.Selection(APPROVAL_TYPE, u'审批类型', related='node_id.type')
    duration = fields.Integer(u'审批时效', related='node_id.duration')
    allow_turn_to = fields.Boolean(u'允许代签')
    allow_before_increase = fields.Boolean(u'允许前加签')
    allow_after_increase = fields.Boolean(u'允许后加签')

    # 结节状态为完成时自动运行
    complete_run = fields.Char(u'节点完成自动运行', help=u'结节状态为完成时自动执行的函数，用英文逗号间隔')

    _sql_constraints = [('flow_node_unique', 'unique(flow_id, node_id)', '节点重复')]

    # @api.onchange('node_id')
    # def node_changed(self):
    #     if self.node_id:
    #         self.name = self.node_id.name

    @api.multi
    def name_get(self):
        record_approval_state_obj = self.env['record.approval.state'].sudo()
        res_users_obj = self.env['res.users'].sudo()

        context = self._context
        res = []

        # 驳回时，显示节点名称和用户
        if 'res_model' in context:
            str_node_ids = json.loads(record_approval_state_obj.search(
                [('model', '=', context['res_model']), ('res_id', '=', context['res_id'])]).str_node_ids)
            for node in self:
                if node.node_id.is_start:
                    res.append((node.id, '%s/%s' % (str(node.id), node.name,)))
                else:
                    users = '，'.join([users.name for users in res_users_obj.browse(list(map(int, list(
                        filter(lambda x: x['node_id'] == node.id, str_node_ids))[0]['user_ids'].split(','))))])
                    res.append((node.id, '%s/%s(%s)' % (str(node.id), node.name, users,)))

        else:
            for node in self:
                res.append((node.id, '%s/%s' % (str(node.id), node.name,)))

        return res

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if 'dont_show_start_end' in self._context:
            args = args or []
            args.append(('node_id', 'not in',
                         [self.env.ref('web_approval.start_node').id, self.env.ref('web_approval.end_node').id]))
        return super(ApprovalFlowNode, self)._search(args, offset=offset, limit=limit, order=order, count=count,
                                                     access_rights_uid=access_rights_uid)

    @api.model
    def create(self, vals):
        # 删除回调方法的空格
        for method in ['completed_run']:
            ApprovalFlow.delete_method_blank(vals, method)

        return super(ApprovalFlowNode, self).create(vals)

    @api.multi
    def write(self, vals):
        # 删除回调方法的空格
        for method in ['completed_run']:
            ApprovalFlow.delete_method_blank(vals, method)

        return super(ApprovalFlowNode, self).write(vals)

    @api.constrains('complete_run')
    def check_complete_run(self):
        for node in self:
            node.flow_id.check_methods_exist(node.complete_run)

    @api.onchange('node_id')
    def node_changed(self):
        if self.node_id:
            self.name = self.node_id.name
            self.allow_turn_to = self.node_id.allow_turn_to
            self.allow_after_increase = self.node_id.allow_after_increase
            self.allow_before_increase = self.node_id.allow_before_increase


class ApprovalFlowNodeAction(models.Model):
    _name = 'approval.flow.node.action'
    _description = u'节点动作'

    flow_id = fields.Many2one('approval.flow', u'流程', ondelete='cascade')
    action_type = fields.Selection([('accept', u'同意'), ('refuse', u'拒绝')], u'动作类型', default='accept')
    condition = fields.Char(u'条件')
    source_node_id = fields.Many2one('approval.flow.node', u'源节点', ondelete='cascade', required=1)
    target_node_id = fields.Many2one('approval.flow.node', u'目标节点', ondelete='cascade', required=1)

    @api.constrains('source_node_id', 'target_node_id', 'condition')
    def check_action(self):
        for action in self:
            if action.source_node_id.id == action.target_node_id.id:
                raise ValidationError('源节点和目标节点不能相同！')

            # 开始节点和结束节点不存在
            if (action.source_node_id.node_id.is_start or action.source_node_id.node_id.is_end) and (
                    action.target_node_id.node_id.is_start or action.target_node_id.node_id.is_end):
                raise ValidationError('开始节点和结束节点之间不能建立动作！')

            if self.search([('flow_id', '=', action.flow_id.id), ('source_node_id', '=', action.source_node_id.id),
                            ('target_node_id', '=', action.target_node_id.id), ('condition', '=', action.condition),
                            ('id', '!=', action.id)]):
                raise ValidationError('动作(%s-->%s)已经存在！' % (action.source_node_id.name, action.target_node_id.name))

            if action.condition:
                action.flow_id.check_condition(action.condition)


class ApprovalFlowInstance(models.Model):
    _name = "approval.flow.instance"
    _description = u'审批流实例'

    flow_id = fields.Many2one('approval.flow', string=u'审批流程', ondelete='cascade', index=True)
    res_id = fields.Integer(u'模型ID')
    model_name = fields.Char(u'模型')
    state = fields.Selection([('active', u'激活'), ('complete', u'完成')], default='active')

    instance_node_ids = fields.One2many('approval.flow.instance.node', 'instance_id', '实例节点')

    # next_instance_node_id = fields.Integer(u'下一实例开始节点')
    #
    # str_node_ids = fields.Char(u'审批节点')
    undone_info = fields.Char(u'未完成的信息')

    # @api.depends('instance_node_ids')
    # def _compute_state(self):
    #     """所有的approval.flow.instance.node的状态为complete，则实例的状态为complete，否则为active"""
    #     for instance in self:
    #         if all([wa.state == 'complete' for wa in instance.instance_node_ids]):
    #             instance.state = 'complete'
    #         else:
    #             instance.state = 'active'


class ApprovalFlowInstanceNode(models.Model):
    _name = "approval.flow.instance.node"
    _description = u"审批流实例节点"

    flow_id = fields.Many2one('approval.flow', string=u'审批流程', ondelete='cascade', index=True)
    node_id = fields.Many2one('approval.flow.node', string=u'节点', ondelete="cascade", index=True)
    instance_id = fields.Many2one('approval.flow.instance', string=u'实例', ondelete="cascade", index=True)
    state = fields.Selection(WAIT_APPROVAL_STATE, index=True, string=u'状态', default='active')

    res_id = fields.Integer(u'记录ID', related='instance_id.res_id', store=1)
    model_name = fields.Char(u'模型', related='instance_id.model_name', store=1)

    serial_num = fields.Integer(u'序号')

    @api.multi
    def write(self, vals):
        res = super(ApprovalFlowInstanceNode, self).write(vals)
        if 'state' in vals:
            for instance_node in self:
                if all([inode.state == 'complete' for inode in
                        self.search([('instance_id', '=', instance_node.instance_id.id)])]):
                    instance_node.instance_id.state = 'complete'

        return res


class WaitApproval(models.Model):
    _name = 'wait.approval'
    _description = u'待审批'

    instance_node_id = fields.Many2one('approval.flow.instance.node', u'实例节点', ondelete='cascade')

    model_name = fields.Char(u'模型', related='instance_node_id.model_name', store=1, index=1)
    res_id = fields.Integer(u'记录ID', related='instance_node_id.res_id', store=1)
    serial_num = fields.Integer(string=u'顺序', related='instance_node_id.serial_num')

    state = fields.Selection(WAIT_APPROVAL_STATE, index=True, string=u'状态')

    apply_id = fields.Many2one('res.users', u'申请人')

    user_id = fields.Many2one('res.users', u'待审批用户', index=1)

    is_turn_to = fields.Boolean('是代签')

    is_parent = fields.Boolean('节点是直属领导的上级或部门领导的上级审批')

    # ####加签相关
    is_increase = fields.Boolean(u'是加签')
    parent_id = fields.Many2one('wait.approval', u'关联节点')
    increase_type = fields.Char(u'加签类型')
    child_ids = fields.One2many('wait.approval', 'parent_id', '加签的节点')

    @api.multi
    def write(self, vals):
        res = super(WaitApproval, self).write(vals)
        if 'state' in vals:
            for wait_approval in self:
                instance_node_id = wait_approval.instance_node_id.id
                if all([wa.state == 'complete' for wa in self.search([('instance_node_id', '=', instance_node_id)])]):
                    wait_approval.instance_node_id.state = 'complete'

        return res


class Approval(models.Model):
    _name = 'approval'
    _description = u'审批'

    wait_approval_id = fields.Many2one('wait.approval', '待审批', ondelete='cascade')
    instance_node_id = fields.Many2one('approval.flow.instance.node', u'实例节点',
                                       related='wait_approval_id.instance_node_id', store=1)
    # action_id = fields.Many2one('approval.flow.node.action', u'动作')
    action_type = fields.Selection([('accept', u'同意'), ('refuse', u'拒绝'), ('turn_to', u'代签')], u'动作类型')
    idea = fields.Text(u'审批意见')

    user_id = fields.Many2one('res.users', u'审批人')

    # res_id = fields.Integer(u'模型ID', related='instance_node_id.res_id', store=1)
    # model_name = fields.Char(u'模型', related='instance_node_id.model_name', store=1)

    copy_for_ids = fields.One2many('approval.copy_for', 'approval_id', u'抄送')
    turn_to_user_id = fields.Many2one('res.users', '代签用户ID')
    refuse_node_id = fields.Many2one('approval.flow.node', '驳回节点')


class ApprovalCopyFor(models.Model):
    _name = 'approval.copy_for'
    _description = u'审批抄送'

    instance_node_id = fields.Many2one('approval.flow.instance.node', u'实例节点', ondelete='cascade')
    approval_id = fields.Many2one('approval', '审批', ondelete='cascade')
    model = fields.Char(u'Model', index=1)
    res_id = fields.Integer(u'记录ID', index=1)
    copy_for_user_id = fields.Many2one('res.users', u'抄送人')
    from_user_id = fields.Many2one('res.users', u'发起抄送')


class RecordApprovalState(models.Model):
    _name = 'record.approval.state'
    _description = u'记录审批状态'

    model = fields.Char(u'Model', index=1)
    model_name = fields.Char('单据', compute='_compute_model_name')
    res_id = fields.Integer(u'记录ID', index=1)
    approval_state = fields.Selection(RECORD_STATE, u'审批状态')
    is_commit_approval = fields.Boolean(u'是否提交审批', default=False)
    commit_user_id = fields.Many2one('res.users', u'提交人')

    flow_id = fields.Many2one('approval.flow', string=u'审批流程')
    str_node_ids = fields.Char(u'审批节点')

    def _compute_model_name(self):
        model_obj = self.env['ir.model']
        for record in self:
            record.model_name = model_obj.search([('model', '=', record.model)]).name

    @api.multi
    def write(self, vals):
        # 流程完成后给文档的创建者发送系统通知，加上链接，可跳转到文档
        if vals.get('approval_state', False) == 'complete':
            model_name = self.env['ir.model'].search([('model', '=', self.model)]).name
            partner_id = self.commit_user_id.sudo().partner_id.id
            self.env['mail.message'].sudo().create({
                # 'subject': model_name,
                'model': self.model,
                'res_id': self.res_id,
                # 'record_name': model_name,
                'body': u'<p>您提交的的%s已审批完成</p>' % model_name,
                'partner_ids': [(6, 0, [partner_id])],
                'needaction_partner_ids': [(6, 0, [partner_id])],
                # 'channel_ids': [(6, 0, [mail_channel_approval.id])],
                'subtype_id': self.env.ref('web_approval.mail_message_subtype_approval').id,
                'message_type': 'notification',
                'author_id': self.env.user.partner_id.id,
                'reply_to': False,
                'email_from': False,
                # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})]
            })

        return super(RecordApprovalState, self).write(vals)


class WaitApprovalSummary(models.Model):
    _name = 'wait.approval.summary'
    _description = u'待审批汇总'
    _auto = False

    model_id = fields.Many2one('ir.model', u'模型', index=True, compute='_compute_model_id')
    model_name = fields.Char(u'模型')

    wait_approval_count = fields.Integer(u'待审批数据')

    res_ids = fields.Char(u'IDS')
    state = fields.Selection(WAIT_APPROVAL_STATE, string=u'状态')
    user_id = fields.Many2one('res.users', u'待审批用户')

    def _compute_model_id(self):
        model_obj = self.env['ir.model']
        for summary in self:
            summary.model_id = model_obj.search([('model', '=', summary.model_name)]).id

    def init(self):
        self._cr.execute("""
        CREATE OR REPLACE VIEW wait_approval_summary AS (
            SELECT 
                ROW_NUMBER() OVER() AS id,
                model_name,
                user_id,
                COUNT(*) AS wait_approval_count,
                string_agg(res_id || '', ',') AS res_ids,
                state
            FROM wait_approval
            GROUP BY model_name, user_id, state
        )
        """)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=80, order=None):
        domain = domain or []
        domain.append(('user_id', '=', self.env.user.id))

        fields = fields or []
        fields += ['res_ids', 'model_name']
        result = super(WaitApprovalSummary, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit,
                                                              order=order)

        res = []
        for r in result:
            ids = list(map(int, r['res_ids'].split(',')))
            count = len(self.env[r['model_name']].search([('id', 'in', ids)]))
            if count > 0:
                r['wait_approval_count'] = count
                res.append(r)
        return res

    @api.model
    def summary_action(self, state, name):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'wait.approval.summary',
            'view_mode': 'kanban',
            'target': 'current',
            'domain': [('state', '=', state)],
            'context': {
                'approval_supper': 1,
                'state': state,
            }
        }

    @api.multi
    def to_approval(self):
        self.ensure_one()

        res_ids = list(map(int, self.res_ids.split(',')))

        if len(res_ids) == 1:
            return {
                'name': u'%s审批' % self.model_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'res_id': res_ids[0],
                'context': {'approval_supper': 1},
            }
        else:
            return {
                'name': u'%s审批' % self.model_id.name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res_ids)],
                'context': {'approval_supper': 1},
            }


class RecordApprovalStateSummary(models.Model):
    _name = 'record.approval.state.summary'
    _description = u'记录审批状态'
    _auto = False

    model_id = fields.Many2one('ir.model', u'模型', index=True, compute='_compute_model_id')
    model_name = fields.Char(u'模型')

    count = fields.Integer(u'抄送数理')

    res_ids = fields.Char(u'IDS')

    approval_state = fields.Selection(RECORD_STATE, u'审批状态')
    commit_user_id = fields.Many2one('res.users', u'提交人')

    def _compute_model_id(self):
        model_obj = self.env['ir.model']
        for summary in self:
            summary.model_id = model_obj.search([('model', '=', summary.model_name)]).id

    def init(self):
        self._cr.execute("""
        CREATE OR REPLACE VIEW record_approval_state_summary AS (
            SELECT 
                ROW_NUMBER() OVER() AS id,
                model AS model_name,
                approval_state,
                commit_user_id,
                COUNT(*) AS count,
                string_agg(res_id || '', ',') AS res_ids
            FROM record_approval_state
            GROUP BY model, commit_user_id, approval_state
        )
        """)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=80, order=None):
        domain = domain or []
        domain.append(('commit_user_id', '=', self.env.user.id))

        fields = fields or []
        fields += ['res_ids', 'model_name']
        result = super(RecordApprovalStateSummary, self).search_read(domain=domain, fields=fields, offset=offset,
                                                                     limit=limit, order=order)

        res = []
        for r in result:
            ids = list(map(int, r['res_ids'].split(',')))
            count = len(self.env[r['model_name']].search([('id', 'in', ids)]))
            if count > 0:
                r['count'] = count
                res.append(r)

        return res

    @api.multi
    def to_approval(self):
        self.ensure_one()

        res_ids = list(map(int, self.res_ids.split(',')))

        states = {
            'active': u'审批中',
            'complete': u'已完成',
            'pause': u'暂停中',
            'cancel': u'已取消',
        }
        approval_state = self._context['approval_state']
        if len(res_ids) == 1:
            return {
                'name': u'%s-%s' % (self.model_id.name, states[approval_state]),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'res_id': res_ids[0],
                'context': {'approval_supper': 1},
            }
        else:
            return {
                'name': u'%s-%s' % (self.model_id.name, states[approval_state]),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res_ids)],
                'context': {'approval_supper': 1},
            }


class ApprovalCopyForSummary(models.Model):
    _name = 'approval.copy_for.summary'
    _description = u'审批抄送汇总'
    _auto = False

    model_id = fields.Many2one('ir.model', u'模型', index=True, compute='_compute_model_id')
    model_name = fields.Char(u'模型')
    copy_for_count = fields.Integer(u'抄送数理')
    res_ids = fields.Char(u'IDS')
    user_id = fields.Many2one('res.users', u'抄送人')

    def _compute_model_id(self):
        model_obj = self.env['ir.model']
        for summary in self:
            summary.model_id = model_obj.search([('model', '=', summary.model_name)]).id

    def init(self):
        self._cr.execute("""
        CREATE OR REPLACE VIEW approval_copy_for_summary AS (
            SELECT 
                ROW_NUMBER() OVER() AS id,
                model AS model_name,
                copy_for_user_id AS user_id,
                COUNT(*) AS copy_for_count,
                string_agg(res_id || '', ',') AS res_ids
            FROM approval_copy_for
            GROUP BY model, copy_for_user_id
        )
        """)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=80, order=None):
        domain = domain or []
        domain.append(('user_id', '=', self.env.user.id))

        fields = fields or []
        fields += ['res_ids', 'model_name']
        result = super(ApprovalCopyForSummary, self).search_read(domain=domain, fields=fields, offset=offset,
                                                                 limit=limit, order=order)

        res = []
        for r in result:
            ids = list(map(int, r['res_ids'].split(',')))
            count = len(self.env[r['model_name']].sudo().search([('id', 'in', ids)]))
            if count > 0:
                r['copy_for_count'] = count
                res.append(r)

        return res

    @api.multi
    def to_approval(self):
        self.ensure_one()

        res_ids = list(set(map(lambda x: int(x), self.res_ids.split(','))))

        if len(res_ids) == 1:
            return {
                'name': u'%s抄送' % self.model_id.name,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'res_id': res_ids[0],
                'context': {'approval_supper': 1},
            }
        else:
            return {
                'name': u'%s抄送' % self.model_id.name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': self.model_id.model,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res_ids)],
                'context': {'approval_supper': 1},
            }


class IncreaseType(models.Model):
    _name = 'increase.type'
    _description = u'加签类型'

    code = fields.Char(u'代码')
    name = fields.Char(u'名称')
