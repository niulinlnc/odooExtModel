# -*- coding: utf-8 -*-
import json
import logging

try:
    import networkx as nx
except ImportError:
    pass

import traceback
import pytz

from odoo import models, api
from odoo.exceptions import ValidationError
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)

def _get_approval_flow(self):
    """获取审批流程"""
    flow_obj = self.env.get('approval.flow')
    if flow_obj is None:
        return

    res_id = self.id
    model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)]).id

    # 有适用公司有条件的审批流程
    domain = [('model_id', '=', model_id), ('company_ids', '!=', False), ('condition', '!=', False)]
    for flow in flow_obj.search(domain, order='id desc'):
        if self.company_id.id in flow.company_ids.ids:
            ids = self.search(eval(flow.condition)).ids
            if res_id in ids:
                return flow

    # 有适用公司无条件的审批流程
    domain = [('model_id', '=', model_id), ('company_ids', '!=', False), ('condition', '=', False)]
    for flow in flow_obj.search(domain, order='id desc'):
        if self.company_id.id in flow.company_ids.ids:
            return flow

    # 无适用公司有条件的审批流程
    domain = [('model_id', '=', model_id), ('company_ids', '=', False), ('condition', '!=', False)]
    for flow in flow_obj.search(domain, order='id desc'):
        ids = self.search(eval(flow.condition)).ids
        if res_id in ids:
            return flow

    # 无适用公司无条件的审批流程
    domain = [('model_id', '=', model_id), ('company_ids', '=', False), ('condition', '=', False)]
    flows = flow_obj.search(domain, order='id desc')
    if flows:
        return flows[0]

@api.multi
def _commit_approval(self):
    """提交审批"""
    def dispatch_approval_user():
        """计算审批流程需指定审批的用户"""
        node_user = []
        for path in paths:
            node = flow_node_obj.browse(path['node_id'])  # 审批流节点
            node_id = node.node_id  # 审批节点
            node_type = node_id.type  # 审批节点审批类型
            if node_type == 'group':
                # 只需一人审批(is_all_approval: 是否需全组审批)
                if not node_id.is_all_approval:
                    if node_id.only_document_company:  # 仅单据公司
                        users = users_obj.search([('company_id', '=', self.company_id.id), ('share', '=', False)])
                    else:
                        users = users_obj.search([('share', '=', False)])

                    exist_users = users.filtered(lambda user: node_id.groups_id.id in user.groups_id.ids)
                    if len(exist_users) > 1:
                        node_user.append({
                            'node_id': node.id,
                            'node_name': node.name,
                            'node_type': node_type,
                            'user_ids': exist_users.ids,
                            'serial_num': path['serial_num'],
                        })

            elif node_type == 'job':
                if not node_id.job_is_all_approval:
                    if node_id.job_only_document_company:  # 仅单据公司
                        employees = employee_obj.search(
                            [('company_id', '=', self.company_id.id), ('job_id', 'in', node_id.job_ids.ids),
                             ('user_id', '!=', False)])
                    else:
                        employees = employee_obj.search(
                            [('job_id', 'in', node_id.job_ids.ids), ('user_id', '!=', False)])

                    user_ids = list(set([employee.user_id.id for employee in employees]))
                    if len(user_ids) > 1:
                        node_user.append({
                            'node_id': node.id,
                            'node_name': node.name,
                            'node_type': node_type,
                            'user_ids': user_ids,
                            'serial_num': path['serial_num'],
                        })

            elif node_type == 'user':
                if not node_id.user_is_all_approval:
                    if node_id.user_only_document_company:
                        user_ids = node_id.user_ids.filtered(lambda user: user.company_id.id == self.company_id.id).ids
                    else:
                        user_ids = node_id.user_ids.ids

                    if len(user_ids) > 1:
                        node_user.append({
                            'node_id': node.id,
                            'node_name': node.name,
                            'node_type': node_type,
                            'user_ids': user_ids,
                            'serial_num': path['serial_num'],
                        })

        if node_user:
            return {
                'name': u'指定审批人',
                'type': 'ir.actions.act_window',
                'res_model': 'dispatch.approval.user.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'views': [[False, 'form']],
                'context': {
                    'node_user': node_user,
                    'model': model,
                    'res_id': res_id,
                    'approval_supper': 1,
                    'flow_id': approval_flow.id
                }
            }

    def create_wait_approval(user_id1, send_message=False, inode=None):
        inode = inode or instance_node
        wait_approval = wait_approval_obj.create({
            'instance_node_id': inode.id,
            'apply_id': self.env.user.id, # 申请人
            'user_id': user_id1, # 待审批用户
            'state': 'running' if send_message else 'active'
        })

        if send_message:
            model_name = model_obj.search([('model', '=', model)]).name
            partner_id = wait_approval.user_id.sudo().partner_id.id
            mail_message_obj.create({
                # 'subject': model_name,
                'model': model,
                'res_id': res_id,
                # 'record_name': model_name,
                'body': u'<p>有%s需要您审批</p>' % model_name,
                'partner_ids': [(6, 0, [partner_id])], # 收件人
                'needaction_partner_ids': [(6, 0, [partner_id])], # 待处理的业务伙伴
                'subtype_id': mail_message_subtype_approval_id, # 子类型
                'message_type': 'notification', # 类型-通知
                'author_id': self.env.user.partner_id.id,
                'reply_to': False,
                'email_from': False,
                # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})], # 通知
                # 'instance_node_id': wait_approval.instance_node_id.id # TODO
            })


    def recommit():
        """再次提交(驳回后再次提交)"""
        instance = instance_obj.search([('res_id', '=', res_id), ('model_name', '=', model), ('state', '=', 'complete'), ], order='id desc', limit=1)
        if instance and instance.undone_info and res_state.str_node_ids:
            undone_info = json.loads(instance.undone_info)
            str_node_ids = json.loads(res_state.str_node_ids)
            # 更新记录审批状态的是否提交审批字段
            res_state.write({
                'is_commit_approval': True,
                'approval_state': 'active',
                # 'commit_user_id': self.env.user.id  # 提交人
            })
            # 创建审批流程实例
            instance = instance_obj.create({
                'flow_id': res_state.flow_id.id,
                'res_id': res_id,
                'model_name': model,
                # 'state': 'active',
            })

            min_serial_num = 1000

            for path in undone_info:
                if not path['user_ids']:
                    continue
                node_id = path['node_id']
                node = list(filter(lambda x: x['node_id'] == node_id, str_node_ids))[0]
                serial_num = node['serial_num']
                if serial_num < min_serial_num:
                    min_serial_num = serial_num

            for path in undone_info:
                if not path['user_ids']:
                    continue

                node_id = path['node_id']
                node = flow_node_obj.browse(node_id)
                if node.node_id.is_start or node.node_id.is_end:
                    continue

                node = list(filter(lambda x: x['node_id'] == node_id, str_node_ids))[0]

                instance_node = instance_node_obj.create({
                    'flow_id': res_state.flow_id.id,
                    'node_id': path['node_id'],
                    'instance_id': instance.id,
                    'serial_num': node['serial_num'],
                    'state': 'running' if node['serial_num'] == min_serial_num else 'active',
                })
                # 创建待审批信息
                for uid in path['user_ids'].split(','):
                    create_wait_approval(int(uid), node['serial_num']==min_serial_num, instance_node)

            return True


    instance_obj = self.env['approval.flow.instance']
    instance_node_obj = self.env['approval.flow.instance.node']
    flow_node_obj = self.env['approval.flow.node'].sudo()
    users_obj = self.env['res.users'].sudo()
    employee_obj = self.env['hr.employee'].sudo()
    record_approval_state_obj = self.env['record.approval.state']
    wait_approval_obj = self.env['wait.approval']
    mail_message_obj = self.env['mail.message'].sudo()
    model_obj = self.env['ir.model'].sudo()

    model = self._name
    res_id = self.id

    instances = instance_obj.search([('res_id', '=', res_id), ('model_name', '=', model), ('state', '=', 'active')])
    if instances:
        raise ValidationError('单据在审批中！')

    res_state = record_approval_state_obj.search([('model', '=', model), ('res_id', '=', res_id)])
    if not res_state:
        raise ValidationError('单据没有对应的记录审批状态')

    mail_message_subtype_approval_id = self.env.ref('web_approval.mail_message_subtype_approval').id

    # 驳回后，再次提交
    if recommit():
        return

    approval_flow = self._get_approval_flow()
    if not approval_flow:
        raise ValidationError('单据没有定义审批流程')

    if not [action for action in approval_flow.action_ids if action.action_type == 'accept']:
        raise ValidationError('单据的审批流程没有定义动作！')

    # 开始节点、结束结点
    start_node = list(filter(lambda node: node.node_id.is_start, approval_flow.node_ids))[0]
    end_node = list(filter(lambda node: node.node_id.is_end, approval_flow.node_ids))[0]

    edges = []  # 边
    for node_action in approval_flow.action_ids:
        if node_action.condition:
            condition = eval(node_action.condition)
            condition += [('id', '=', res_id)]
            if self.search(condition):
                edges.append((node_action.source_node_id.id, node_action.target_node_id.id))
        else:
            edges.append((node_action.source_node_id.id, node_action.target_node_id.id))

    # 创建图
    G = nx.DiGraph(edges)
    try:
        # 整个审批流程的所有路径
        all_paths = [path for path in nx.all_simple_paths(G, source=start_node.id, target=end_node.id)]
    except nx.NodeNotFound:
        raise ValidationError('单据流程定义错误，应以开始节点开始，以结束节点结束！')

    # start_node_id = start_node.id
    # real_paths = [path[path.index(start_node_id):] for path in all_paths]

    edges = []  # 边
    for path in all_paths:
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])

            if edge not in edges:
                edges.append(edge)

    # 创建图
    G = nx.DiGraph(edges)
    in_degree = {} # 入度
    for source, target in edges:
        in_degree.setdefault(target, []).append(source)

    # 入度为0的节点
    source = [v for v, d in G.in_degree() if d == 0]
    [in_degree.update({s: []}) for s in source]

    paths = []
    serial_num = 0
    while source:
        for s in source:
            in_degree.pop(s)
            paths.append({
                'node_id': s,
                'serial_num': serial_num
            })
            for d in in_degree.keys():
                if s in in_degree[d]:
                    in_degree[d].remove(s)

        source = [v for v in in_degree.keys() if len(in_degree[v]) == 0]
        serial_num += 10

    _logger.info(u'审批路径：%s', json.dumps(paths, indent=4))
    if not paths:
        raise ValidationError('单据没有适用的审批流程！')

    action = dispatch_approval_user()
    if action:
        return action

    instance = instance_obj.create({
        'flow_id': approval_flow.id,
        'res_id': res_id,
        'model_name': model,
        # 'state': 'active', # [('active', u'激活'), ('complete', u'完成')]
        # 'str_node_ids': json.dumps(paths)
    })
    min_serial_num = 10

    for path in paths:
        node_id = path['node_id']
        node = flow_node_obj.browse(node_id)
        node_id = node.node_id
        node_type = node_id.type
        if node_id.is_start or node_id.is_end:
            continue

        instance_node = instance_node_obj.create({
            'flow_id': approval_flow.id,
            'node_id': path['node_id'],
            'instance_id': instance.id,
            'serial_num': path['serial_num'],
            'state': 'running' if path['serial_num'] == min_serial_num else 'active', # [('active', u'草稿'), ('running', u'正在审批'), ('complete', u'完成')]
            # 'group_user_id': False,  # 组指定审批人
            # 'job_user_id': False,  # 岗位指定审批人
            # 'user_user_id': False  # 用户指定审批人
        })

        # 创建待审批
        if node_type == 'group':
            if node_id.only_document_company:
                user_ids = node_id.groups_id.users.filtered(lambda user: user.company_id.id == self.company_id.id).ids
            else:
                user_ids = node_id.groups_id.users.ids

            if not user_ids:
                raise ValidationError(u'节点%s的审批组没有用户，不能送审！' % (node.name,))

            path_user_ids = []
            for user_id in user_ids:
                create_wait_approval(user_id, path['serial_num'] == min_serial_num)
                path_user_ids.append(str(user_id))

            path.update({'user_ids': ','.join(path_user_ids)})

        elif node_type == 'job':
            if node_id.job_only_document_company:
                employees = employee_obj.search([('company_id', '=', self.company_id.id), ('job_id', 'in', node_id.job_ids.ids), ('user_id', '!=', False)])
            else:
                employees = employee_obj.search([('job_id', 'in', node_id.job_ids.ids), ('user_id', '!=', False)])

            if not employees:
                raise ValidationError(u'节点%s的岗位没有员工，不能送审！' % (node.name,))

            user_ids = list(set([employee.user_id.id for employee in employees]))
            if not user_ids:
                raise ValidationError(u'节点%s的岗位的员工没有用户，不能送审！' % (node.name,))

            path_user_ids = []
            for user_id in user_ids:
                create_wait_approval(user_id, path['serial_num'] == min_serial_num)
                path_user_ids.append(str(user_id))

            path.update({'user_ids': ','.join(path_user_ids)})

        elif node_type == 'user':
            if node_id.user_only_document_company:
                user_ids = node_id.user_ids.filtered(lambda user: user.company_id.id == self.company_id.id).ids
            else:
                user_ids = node_id.user_ids.ids

            if not user_ids:
                raise ValidationError(u'节点%s的没有适合条件的用户，不能送审！' % (node.name,))

            path_user_ids = []
            for user_id in user_ids:
                create_wait_approval(user_id, path['serial_num'] == min_serial_num)
                path_user_ids.append(str(user_id))

            path.update({'user_ids': ','.join(path_user_ids)})

        elif node_type == 'leader':
            employee = getattr(self, 'employee_id', False)
            if not employee:
                raise ValidationError('单据没有员工属性或未设置员工的值，不能为节点%s指定直属领导审批类型！' % (node.name, ))

            parent = employee.parent_id
            if not parent:
                raise ValidationError(u'员工%s没有直属领导，不能为节点%s指定直属领导审批类型！' % (employee.name, node.name))

            user_id = parent.user_id
            if not user_id:
                raise ValidationError(u'没有为员工%s的直属领导%s绑定用户，不能为节点%s指定直属领导审批类型！' % (employee.name, parent.name, node.name))

            user_id = user_id.id
            create_wait_approval(user_id, path['serial_num'] == min_serial_num)
            path.update({'user_ids': str(user_id)})

        elif node.type == 'department_head':
            employee = getattr(self, 'employee_id', False)
            if not employee:
                raise ValidationError('单据没有员工属性或未设置员工的值，不能为节点%s指定部门领导审批类型！' % (node.name, ))

            department = employee.department_id
            if not department:
                raise ValidationError(u'员工%s没有设置部门属性，不能为节点%s指定部门领导审批类型！' % (employee.name, node.name))

            manager = department.manager_id
            if not manager:
                raise ValidationError(u'部门%s没有管理员，不能为节点%s指定部门领导审批类型！' % (department.name, node.name))

            user_id = manager.user_id
            if not user_id:
                raise ValidationError(u'部门%s管理员%s绑定用户，不能为节点%s指定部门领导审批类型！' % (department.name, manager.name, node.name))

            user_id = user_id.id
            create_wait_approval(user_id, path['serial_num'] == min_serial_num)
            path.update({'user_ids': str(user_id)})

    res_state.write({
        'is_commit_approval': True,
        'approval_state': 'active',
        'commit_user_id': self.env.user.id,  # 提交人
        'flow_id': approval_flow.id, # 审批流程
        'str_node_ids': json.dumps(paths)
    })
    # 提交自动运行
    if approval_flow.commit_run:
        for method in approval_flow.commit_run.split(','):
            getattr(self, method.strip())()

@api.one
def _pause_approval(self):
    """暂停审批"""
    record_approval_state = self.env['record.approval.state'].search([('model', '=', self._name), ('res_id', '=', self.id)])
    record_approval_state.approval_state = 'pause'

@api.one
def _resume_approval(self):
    """恢复审批"""
    record_approval_state = self.env['record.approval.state'].search([('model', '=', self._name), ('res_id', '=', self.id)])
    record_approval_state.approval_state = 'active'

@api.one
def _cancel_approval(self):
    """取消审批"""
    model = self._name
    res_id = self.id

    record_approval_state = self.env['record.approval.state'].search([('model', '=', model), ('res_id', '=', res_id)])
    record_approval_state.approval_state = 'active'

    # 取消审批不保留审批信息
    for instance in self.env['approval.flow.instance'].search([('model_name', '=', model), ('res_id', '=', res_id)]):
        instance.unlink()

    # 删除消息
    self.env['mail.message'].sudo().search([('model', '=', model), ('res_id', '=', res_id), ('subtype_id', '=', self.env.ref('web_approval.mail_message_subtype_approval').id)]).unlink()

    # 取消自动运行
    approval_flow = record_approval_state.flow_id
    if approval_flow.cancel_run:
        for method in approval_flow.cancel_run.split(','):
            try:
                getattr(self, method.strip())()
            except:
                _logger.error(u'取消model: %s, res_id: %s审批，运行%s方法出错！', model, res_id, method)
                _logger.error(traceback.format_exc())

    record_approval_state.write({
        'approval_state': 'cancel',
        'is_commit_approval': False,
        # 'commit_user_id': False,
        'flow_id': False
    })

def _get_common_approval_buttons_state(self, current_uid):
    """返回审批的提交审批、暂停、恢复、取消审批按钮状态"""
    def get_commit_approval_btn_state():
        """计算提交审批按钮状态"""
        # 记录审批状态不存在或已提交审批或文档的创建者不等于当前用户
        if not record_approval_state or record_approval_state.is_commit_approval or not is_create:
            return False

        return True

    def get_pause_approval_btn_state():
        """计算暂停审批按钮状态"""
        # 记录审批状态不存在或记录审批状态的状态的值不为active或文档的创建者不等于当前用户
        if not record_approval_state or approval_state != 'active' or not is_create:
            return False

        return True

    def get_resume_approval_btn_state():
        """计算恢复审批按钮状态"""
        # 记录审批状态不存在或记录审批状态的状态的值不为active或文档的创建者不等于当前用户
        if not record_approval_state or approval_state != 'pause' or not is_create:
            return False

        return True

    def get_cancel_approval_btn_state():
        """计算取消审批按钮状态"""
        # 记录审批状态不存在或记录审批状态的状态的值不为active或文档的创建者不等于当前用户
        if not record_approval_state or approval_state != 'active' or not is_create:
            return False

        return True

    record_approval_state = self.env['record.approval.state'].search([('model', '=', self._name), ('res_id', '=', self.id)])
    is_create = False
    if getattr(self, 'create_uid', False):
        is_create = self.create_uid.id == current_uid
    approval_state = record_approval_state.approval_state

    return {
        'commit_approval': get_commit_approval_btn_state(), # 提交审批按钮
        'pause_approval': get_pause_approval_btn_state(), # 暂停审批
        'resume_approval': get_resume_approval_btn_state(), # 恢复审批
        'cancel_approval': get_cancel_approval_btn_state(), # 取消审批
        'chatter_approval': len(record_approval_state) > 0 # Chatter审批信息按钮
    }

@api.one
def _get_approval_info(self):
    """获取审批信息"""
    def get_node_name():
        """计算实例节点名称：所有待审批(非转签)用户名称"""
        user_names = '，'.join([wait_approval.user_id.name for wait_approval in wait_approvals if not wait_approval.is_turn_to])
        res = '%s(%s)' % (instance_node.node_id.name, user_names)

        return res

    def get_increase_node_name():
        """计算加签节点名称"""
        return '%s(%s)' % (instance_node.node_id.name, wait_approval.parent_id.user_id.name)


    def get_swap(wa):
        """沟通信息"""
        swaps = []

        for channel in channel_obj.search([('wait_approval_id', '=', wa.id)]):
            # Datetime.to_string(local_tz.localize(approval.create_date))
            items = [{
                'userName': message.author_id.name,
                # 'date': Datetime.to_string(message.create_date.astimezone(timezone)),
                'date':Datetime.to_string(local_tz.localize(message.create_date)),
                'content': message.body
            }for message in message_obj.search([('model', '=', 'mail.channel'), ('res_id', '=', channel.id)], order='id')]
            if not items:
                continue

            partner = channel.channel_partner_ids.filtered(lambda x: x.id != channel.create_uid.partner_id.id)
            swaps.append({
                'title': {'user1': channel.create_uid.name, 'user2': partner.name},
                'items': items
            })

        return swaps

    record_approval_state_obj = self.env['record.approval.state']
    instance_obj = self.env['approval.flow.instance'].sudo()
    instance_node_obj = self.env['approval.flow.instance.node'].sudo()
    wait_approval_obj = self.env['wait.approval'].sudo()
    approval_obj = self.env['approval'].sudo()
    channel_obj = self.env['mail.channel'].with_context(active_test=False).sudo()
    message_obj = self.env['mail.message'].sudo()

    current_uid = self.env.user.id
    tz = self.env.user.tz or 'Asia/Chongqing'
    local_tz = pytz.timezone(tz)

    self = self.sudo()
    # 表单Header部分的审批按钮的状态
    button_state = _get_common_approval_buttons_state(self, current_uid)

    model = self._name
    res_id = self.id

    result = {
        'buttonState': button_state
    }
    res_state = record_approval_state_obj.search([('model', '=', model), ('res_id', '=', res_id)]) # 记录审批状态


    approval_info = []
    for instance in instance_obj.search([('model_name', '=', model), ('res_id', '=', res_id)], order='id desc'):
        instance_approvaled = False  # 该实例当前用户是否已审批

        for instance_node in instance_node_obj.sudo().search([('instance_id', '=', instance.id)], order='serial_num desc, id desc'):

            wait_approvals = wait_approval_obj.search([('instance_node_id', '=', instance_node.id)], order='serial_num asc, id desc') # 实例节点对应的待审批
            wait_approvals_copy = []
            for wait_approval in wait_approvals:
                approval = approval_obj.search([('wait_approval_id', '=', wait_approval.id)], order='id desc', limit=1)
                if approval:
                    setattr(wait_approval, 'sort_date', approval.create_date)
                else:
                    setattr(wait_approval, 'sort_date', wait_approval.create_date)

                wait_approvals_copy.append(wait_approval)

            wait_approvals_copy = sorted(wait_approvals_copy, key=lambda x: getattr(x, 'sort_date'), reverse=True)


            approvals = []
            node_name = get_node_name() # 节点名称
            unapproval_wait_approval = [] # 没有审批的待审批节点

            for wait_approval in wait_approvals_copy:
                approval = approval_obj.search([('wait_approval_id', '=', wait_approval.id)], order='id desc', limit=1)
                if approval:
                    if approval.user_id.id == current_uid:
                        instance_approvaled = True

                if wait_approval.is_turn_to:
                    if approval:
                        approvals.append({
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': 'complete',
                            'isMine': approval.user_id.id == current_uid,
                            'actionType': approval.action_type,
                            'nodeName': '%s转(%s)' % (node_name, wait_approval.user_id.name),
                            'refuseNode': approval.refuse_node_id.name,  # 驳回节点
                            'turnToNode': False,  # 转签节点名称
                            # 'canTurnTo': instance_node.node_id.node_id.allow_turn_to,  # 当前节点是否可转签
                            'canTurnTo': False,  # 当前节点是否可转签
                            'allowIncrease': False,  # 允许加签
                            'approval': {  # 审批信息
                                'userName': approval.user_id.name,  # 审批用户名
                                'approvalDate': Datetime.to_string(approval.create_date.replace(tzinfo=pytz.utc).astimezone(local_tz)), #
                                'idea': approval.idea,  # 审批意见
                                'copyFor': '，'.join([copy_for.copy_for_user_id.name for copy_for in approval.copy_for_ids]) or False, # 抄送
                                'swap': get_swap(wait_approval)
                            }
                        })
                    else:
                        is_mine = not instance_approvaled and current_uid == wait_approval.user_id.id
                        approvals.append({
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': instance_node.state,
                            'isMine': is_mine,
                            'actionType': False,
                            'nodeName': '%s转(%s)' % (node_name, wait_approval.user_id.name),
                            'refuseNode': False,
                            'turnToNode': False,  # 转签节点名称
                            'canTurnTo': False,  # 当前节点是否可转签
                            'allowIncrease': False,  # 允许加签
                            'approval': {
                                'swap': get_swap(wait_approval)
                            },  # 审批信息
                        })
                elif wait_approval.is_increase:
                    if approval:
                        approvals.append({
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': 'complete',
                            'isMine': approval.user_id.id == current_uid,
                            'actionType': approval.action_type,
                            'nodeName': '%s加(%s)' % (get_increase_node_name(), wait_approval.user_id.name),
                            'refuseNode': approval.refuse_node_id.name,  # 驳回节点
                            'turnToNode': False,  # 转签节点名称
                            # 'canTurnTo': instance_node.node_id.node_id.allow_turn_to,  # 当前节点是否可转签
                            'canTurnTo': False,  # 当前节点是否可转签
                            'allowIncrease': False,  # 允许加签
                            'approval': {  # 审批信息
                                'userName': approval.user_id.name,  # 审批用户名
                                # 'approvalDate': Datetime.to_string(approval.create_date.astimezone(timezone)),
                                'approvalDate': Datetime.to_string(local_tz.localize(approval.create_date)),  #
                                'idea': approval.idea,  # 审批意见
                                'copyFor': '，'.join([copy_for.copy_for_user_id.name for copy_for in approval.copy_for_ids]) or False, # 抄送
                                'swap': get_swap(wait_approval)
                            }
                        })
                    else:
                        is_mine = not instance_approvaled and current_uid == wait_approval.user_id.id
                        approvals.append({
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': instance_node.state,
                            'isMine': is_mine,
                            'actionType': False,
                            'nodeName': '%s加(%s)' % (get_increase_node_name(), wait_approval.user_id.name),
                            'refuseNode': False,
                            'turnToNode': False,  # 转签节点名称
                            'canTurnTo': False,  # 当前节点是否可转签
                            'allowIncrease': False,  # 允许加签
                            'approval': {
                                'swap': get_swap(wait_approval)
                            },  # 审批信息
                        })
                else:
                    if approval:
                        approvals.append({
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': 'complete',
                            'isMine': approval.user_id.id == current_uid,
                            'actionType': approval.action_type,
                            'nodeName': '%s转(%s)' % (node_name, wait_approval.user_id.name) if wait_approval.is_turn_to else node_name,
                            'refuseNode': approval.refuse_node_id.name,  # 驳回节点
                            'turnToNode': False if not approval.turn_to_user_id else '转(%s)审批' % (approval.turn_to_user_id.name,),  # 转签节点名称
                            'canTurnTo': False,  # 当前节点是否可转签
                            'allowIncrease': False,  # 允许加签
                            'approval': {  # 审批信息
                                'userName': approval.user_id.name,  # 审批用户名
                                'approvalDate': Datetime.to_string(approval.create_date.replace(tzinfo=pytz.utc).astimezone(local_tz)),  #
                                'idea': approval.idea,  # 审批意见
                                'copyFor': '，'.join([copy_for.copy_for_user_id.name for copy_for in approval.copy_for_ids]) or False, # 抄送
                                'swap': get_swap(wait_approval)
                            }
                        })
                    else:
                        unapproval_wait_approval.append(wait_approval)

            if unapproval_wait_approval:
                exist = False
                for wait_approval in unapproval_wait_approval:
                    if wait_approval.user_id.id == current_uid:
                        approvals.insert(0, {
                            'instance_node_id': instance_node.id,
                            'wait_approval_id': wait_approval.id,
                            'res_model': model,
                            'res_id': res_id,
                            'state': instance_node.state,
                            'isMine': True,
                            'actionType': False,
                            'nodeName': node_name,
                            'refuseNode': False,
                            'turnToNode': False,  # 转签节点名称
                            'canTurnTo': instance_node.node_id.allow_turn_to,  # 当前节点是否可转签
                            'allowIncrease': not wait_approval.is_increase and (instance_node.node_id.allow_before_increase or instance_node.node_id.allow_after_increase),  # 允许加签
                            'approval': {
                                'swap': get_swap(wait_approval)
                            },  # 审批信息
                        })
                        exist = True
                        break

                if not exist:
                    # is_mine = not instance_approvaled and current_uid in [wait_approval.user_id.id for wait_approval in wait_approvals]
                    approvals.insert(0, {
                        'instance_node_id': instance_node.id,
                        'wait_approval_id': False,
                        'res_model': model,
                        'res_id': res_id,
                        'state': instance_node.state,
                        'isMine': False,
                        'actionType': False,
                        'nodeName': node_name,
                        'refuseNode': False,
                        'turnToNode': False,  # 转签节点名称
                        'canTurnTo': instance_node.node_id.allow_turn_to,  # 当前节点是否可转签
                        'allowIncrease': instance_node.node_id.allow_before_increase or instance_node.node_id.allow_after_increase,  # 允许加签
                        'approval': {},  # 审批信息
                    })

            approval_info.extend(approvals)

        # 提交
        approval_info.append({
            'instance_node_id': False,
            'wait_approval_id': False,
            'res_model': model,
            'res_id': res_id,
            'state': 'complete',
            'isMine': False,
            'actionType': 'commit',
            'nodeName': False,
            'refuseNode': False,
            'turnToNode': False,
            'canTurnTo': False,
            'approval': {
                'userName': False,
                'approvalDate': False,
                'idea': '%s %s 提交' % (instance.create_uid.name if instance.create_uid.id != 1 else '系统', Datetime.to_string(instance.create_date.replace(tzinfo=pytz.utc).astimezone(local_tz))),
                'copyFor': False,
                'swap': []
            },
        })

    # 审批信息
    approvalInfo = {
        'approvalState': self.doc_approval_state if res_state else '', # 单据审批状态
        'approvalInfos': approval_info,
    }

    result.update({
        'approvalInfo': approvalInfo
    })

    return result


Model = models.Model
setattr(Model, 'commit_approval', _commit_approval)
setattr(Model, 'pause_approval', _pause_approval)
setattr(Model, 'resume_approval', _resume_approval)
setattr(Model, 'cancel_approval', _cancel_approval)
setattr(Model, 'get_approval_info', _get_approval_info)
setattr(Model, '_get_approval_flow', _get_approval_flow)


