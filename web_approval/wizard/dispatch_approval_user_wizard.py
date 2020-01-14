# -*- coding: utf-8 -*-
try:
    import networkx as nx
except ImportError:
    pass
import json
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DispatchApprovalUserWizard(models.TransientModel):
    _name = 'dispatch.approval.user.wizard'
    _description = '指定审批节点的审批用户'

    def _default_line_ids(self):
        node_user = self._context['node_user']
        node_user.sort(key=lambda x: x['serial_num'])
        res = [(0, 0, {
            'node_id': node['node_id'],
            'node_type': node['node_type'],
            'node_name': node['node_name'],
            'user_id_domain': ','.join(map(lambda x: str(x), node['user_ids']))})
               for node in node_user]
        return res

    line_ids = fields.One2many('dispatch.approval.user.wizard.line', 'wizard_id', '审批用户', default=_default_line_ids)


    @api.multi
    def button_ok(self):
        def get_node_user(nid):
            for line in self.line_ids:
                if line.node_id.id == nid:
                    return line.user_id.id

        def create_wait_approval(user_id1, send_message=False, inode=None):
            inode = inode or instance_node
            wait_approval = wait_approval_obj.create({
                'instance_node_id': inode.id,
                'apply_id': self.env.user.id,  # 申请人
                'user_id': user_id1,  # 待审批用户
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
                    'body': '<p>有%s需要您审批</p>' % model_name,
                    'partner_ids': [(6, 0, [partner_id])],  # 收件人
                    'needaction_partner_ids': [(6, 0, [partner_id])],  # 待处理的业务伙伴
                    'subtype_id': mail_message_subtype_approval_id,  # 子类型
                    'message_type': 'notification',  # 类型-通知
                    'author_id': self.env.user.partner_id.id,
                    'reply_to': False,
                    'email_from': False,
                    # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})],  # 通知
                    # 'instance_node_id': wait_approval.instance_node_id.id # TODO
                })

        instance_obj = self.env['approval.flow.instance']
        instance_node_obj = self.env['approval.flow.instance.node']
        flow_node_obj = self.env['approval.flow.node'].sudo()
        # users_obj = self.env['res.users'].sudo()
        employee_obj = self.env['hr.employee'].sudo()
        record_approval_state_obj = self.env['record.approval.state']
        wait_approval_obj = self.env['wait.approval']
        mail_message_obj = self.env['mail.message'].sudo()
        model_obj = self.env['ir.model'].sudo()
        flow_obj = self.env['approval.flow']

        model = self._context['model']
        res_id = self._context['res_id']
        flow_id = self._context['flow_id']

        document = self.env[model].sudo().browse(res_id)  # 当前记录

        res_state = record_approval_state_obj.search([('model', '=', model), ('res_id', '=', res_id)])

        mail_message_subtype_approval_id = self.env.ref('web_approval.mail_message_subtype_approval').id

        approval_flow = flow_obj.browse(flow_id)

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

        # 整个审批流程的所有路径
        all_paths = [path for path in nx.all_simple_paths(G, source=start_node.id, target=end_node.id)]

        edges = []  # 边
        for path in all_paths:
            for i in range(len(path) - 1):
                edge = (path[i], path[i + 1])

                if edge not in edges:
                    edges.append(edge)

        # 创建图
        G = nx.DiGraph(edges)
        in_degree = {}  # 入度
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

        _logger.info('审批路径：%s', json.dumps(paths, indent=4))

        instance = instance_obj.create({
            'flow_id': approval_flow.id,
            'res_id': res_id,
            'model_name': model,
            # 'state': 'active', # [('active', '激活'), ('complete', '完成')]
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
                'state': 'running' if path['serial_num'] == min_serial_num else 'active', # [('active', '草稿'), ('running', '正在审批'), ('complete', '完成')]
            })

            user_id = get_node_user(path['node_id'])
            # 创建待审批
            if node_type == 'group':
                if user_id:
                    user_ids = [user_id]
                else:
                    if node_id.only_document_company:
                        user_ids = node_id.groups_id.users.filtered(lambda user: user.company_id.id == document.company_id.id).ids
                    else:
                        user_ids = node_id.groups_id.users.ids

                for user_id in user_ids:
                    create_wait_approval(user_id, path['serial_num'] == min_serial_num)

                path.update({'user_ids': ','.join(list(map(str, user_ids)))})

            elif node_type == 'job':
                if user_id:
                    user_ids = [user_id]
                else:
                    if node_id.job_only_document_company:
                        employees = employee_obj.search([('company_id', '=', document.company_id.id), ('job_id', 'in', node_id.job_ids.ids), ('user_id', '!=', False)])
                    else:
                        employees = employee_obj.search([('job_id', 'in', node_id.job_ids.ids), ('user_id', '!=', False)])

                    user_ids = list(set([employee.user_id.id for employee in employees]))

                for user_id in user_ids:
                    create_wait_approval(user_id, path['serial_num'] == min_serial_num)

                path.update({'user_ids': ','.join(list(map(str, user_ids)))})

            elif node_type == 'user':
                if user_id:
                    user_ids = [user_id]
                else:
                    if node_id.user_only_document_company:
                        user_ids = node_id.user_ids.filtered(lambda user: user.company_id.id == document.company_id.id).ids
                    else:
                        user_ids = node_id.user_ids.ids

                for user_id in user_ids:
                    create_wait_approval(user_id, path['serial_num'] == min_serial_num)

                path.update({'user_ids': ','.join(list(map(str, user_ids)))})

            elif node_type == 'leader':
                employee = getattr(document, 'employee_id', False)
                if not employee:
                    raise ValidationError('单据没有员工属性或未设置员工的值，不能为节点%s指定直属领导审批类型！' % (node.name,))

                parent = employee.parent_id
                if not parent:
                    raise ValidationError('员工%s没有直属领导，不能为节点%s指定直属领导审批类型！' % (employee.name, node.name))

                user_id = parent.user_id
                if not user_id:
                    raise ValidationError('没有为员工%s的直属领导%s绑定用户，不能为节点%s指定直属领导审批类型！' % (employee.name, parent.name, node.name))

                user_id = user_id.id
                create_wait_approval(user_id, path['serial_num'] == min_serial_num)
                path.update({'user_ids': str(user_id)})

            elif node.type == 'department_head':
                employee = getattr(document, 'employee_id', False)
                if not employee:
                    raise ValidationError('单据没有员工属性或未设置员工的值，不能为节点%s指定部门领导审批类型！' % (node.name,))

                department = employee.department_id
                if not department:
                    raise ValidationError('员工%s没有设置部门属性，不能为节点%s指定部门领导审批类型！' % (employee.name, node.name))

                manager = department.manager_id
                if not manager:
                    raise ValidationError('部门%s没有管理员，不能为节点%s指定部门领导审批类型！' % (department.name, node.name))

                user_id = manager.user_id
                if not user_id:
                    raise ValidationError('部门%s管理员%s绑定用户，不能为节点%s指定部门领导审批类型！' % (department.name, manager.name, node.name))

                user_id = user_id.id
                create_wait_approval(user_id, path['serial_num'] == min_serial_num)
                path.update({'user_ids': str(user_id)})

        res_state.write({
            'is_commit_approval': True,
            'approval_state': 'active',
            'commit_user_id': self.env.user.id,  # 提交人
            'flow_id': approval_flow.id,  # 审批流程
            'str_node_ids': json.dumps(paths)
        })
        # 提交自动运行
        if approval_flow.commit_run:
            for method in approval_flow.commit_run.split(','):
                getattr(document, method.strip())()



class DispatchApprovalUserWizardLine(models.TransientModel):
    _name = 'dispatch.approval.user.wizard.line'
    _description = '指定审批节点的审批用户明细'

    wizard_id = fields.Many2one('dispatch.approval.user.wizard', '向导')
    node_id = fields.Many2one('approval.flow.node', string='节点')
    node_name = fields.Char('审批节点')

    node_type = fields.Selection([('group', '组'), ('user', '用户'), ('job', '岗位')], '审批类型')

    user_id = fields.Many2one('res.users', '审批用户')
    user_id_domain = fields.Char('')

    @api.model
    def create(self, vals):
        if not vals.get('user_id'):
            raise ValidationError('请为节点指定审批用户！')

        return super(DispatchApprovalUserWizardLine, self).create(vals)





