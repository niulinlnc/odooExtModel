# -*- coding: utf-8 -*-
import json

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ApprovalWizard(models.TransientModel):
    _name = 'approval.wizard'
    _description = '审批'

    idea = fields.Text(u'审批意见')
    action_type = fields.Selection([('accept', u'同意'), ('refuse', u'驳回')], u'动作类型', default='accept')
    return_node = fields.Many2one('approval.flow.node', u'驳回节点')

    copy_for_ids = fields.Many2many('res.users', 'approval_wizard_users_rel', 'wizard_id', 'user_id',  string=u'抄送')

    @api.onchange('action_type')
    def onchange_action_type(self):
        action_type = self.action_type
        if not action_type:
            return

        # instance_node_obj = self.env['approval.flow.instance.node']
        record_approval_state_obj = self.env['record.approval.state']
        wait_approval_obj = self.env['wait.approval']

        wait_approval = wait_approval_obj.browse(self._context['wait_approval_id'])

        instance_node = wait_approval.instance_node_id
        approval_flow = instance_node.flow_id

        if action_type == 'accept':
            if approval_flow.accept_template:
                self.idea = approval_flow.accept_template

            return {
                'domain': {
                    'copy_for_ids': [('share', '=', False), ('id', '!=', self.env.user.id)]
                },
            }

        if action_type == 'refuse':
            if approval_flow.refuse_template:
                self.idea = approval_flow.refuse_template

            # 驳回到任意节点
            res_state = record_approval_state_obj.search([('model', '=', self._context['res_model']), ('res_id', '=', self._context['res_id'])])  # 记录审批状态
            node_ids = []
            str_node_ids = json.loads(res_state.str_node_ids)

            # 加签处理
            if wait_approval.is_increase:
                instance_node_serial_num = wait_approval.serial_num
            else:
                instance_node_serial_num = list(filter(lambda x: x['node_id'] == instance_node.node_id.id, str_node_ids))[0]['serial_num'] # 当前节点审批顺序号

            for node_info in str_node_ids:
                if node_info['serial_num'] == instance_node_serial_num:
                    # 节点是直属领导的上级或部门领导的上级审批
                    # wait_approval = wait_approval_obj.search([('instance_node_id', '=', instance_node.id), ('user_id', '=', self.env.user.id)])
                    if wait_approval.is_parent:
                        node_ids.append(node_info['node_id'])
                elif node_info['serial_num'] < instance_node_serial_num:
                    node_ids.append(node_info['node_id'])


            return {
                'domain': {
                    'return_node': [('id', 'in', node_ids)],
                },
            }

    def create_copy_for(self, approval_id, model, res_id, copy_for_user_id, from_user_id):
        """创建抄送"""
        copy_for_obj = self.env['approval.copy_for'].sudo()
        copy_for_obj.create({
            'approval_id': approval_id,
            'model': model,
            'res_id': res_id,
            'copy_for_user_id': copy_for_user_id,
            'from_user_id': from_user_id
        })


    def copy_for(self, approval, model, res_id):
        """创建抄送"""
        for copy_for_user_id in self.copy_for_ids:
            self.create_copy_for(approval.id, model, res_id, copy_for_user_id.id, self.env.user.id)


    def create_approval(self, wait_approval, action_type, model, res_id):
        """创建审批"""
        approval_obj = self.env['approval']
        vals = {
            'wait_approval_id': wait_approval.id,
            'action_type': action_type,
            'idea': self.idea,
            'user_id': self.env.user.id
        }
        if action_type == 'refuse':
            vals['refuse_node_id'] = self.return_node.id

        approval = approval_obj.create(vals)

        if action_type == 'accept' and self.copy_for_ids:
            self.copy_for(approval, model, res_id)


    def send_message(self, partner_id, model, res_id, model_name, mail_message_subtype_approval_id):
        """发送系统通知"""
        mail_message_obj = self.env['mail.message'].sudo()
        mail_message_obj.create({
            # 'subject': model_name,
            'model': model,
            'res_id': res_id,
            # 'record_name': model_name,
            'body': u'<p>有%s需要您审批</p>' % model_name,
            'partner_ids': [(6, 0, [partner_id])],  # 收件人
            'needaction_partner_ids': [(6, 0, [partner_id])],  # 待处理的业务伙伴
            'subtype_id': mail_message_subtype_approval_id,  # 子类型
            'message_type': 'notification',  # 类型-通知
            'author_id': self.env.user.partner_id.id,
            'reply_to': False,
            'email_from': False,
        })


    def approval_done(self, res_state, document, model, res_id, model_name, mail_message_subtype_approval_id):
        """审批完成"""
        employee_obj = self.env['hr.employee'].sudo()
        users_obj = self.env['res.users'].sudo()

        # instance_node.instance_id.state = 'complete'
        approval_flow = res_state.flow_id

        res_state.approval_state = 'complete'
        # 流程完成执行
        if approval_flow.completed_run:
            for method in approval_flow.completed_run.split(','):
                getattr(document.with_context(approval_callback=1), method.strip())()
                document.with_context(approval_callback=0)

        # 完成后发送通知
        user_ids = []
        if approval_flow.complete_copy_for_type == 'user':
            user_ids = approval_flow.complete_copy_for_user_ids

        if approval_flow.complete_copy_for_type == 'job':
            job_ids = approval_flow.complete_copy_for_job_ids.ids
            user_ids = [employee.user_id for employee in employee_obj.search([('job_id', 'in', job_ids), ('user_id', '!=', False)])]

        if user_ids:
            if approval_flow.complete_copy_for_only_document_company:
                user_ids = [user.id for user in filter(lambda x: x.company_id.id == document.company_id.id, user_ids)]
            else:
                user_ids = [user.id for user in user_ids]

            for user in users_obj.browse(user_ids):
                self.send_message(user.partner_id.id, model, res_id, model_name, mail_message_subtype_approval_id)
                self.create_copy_for(False, model, res_id, user.id, self.env.user.id)


    @api.multi
    def button_ok(self):
        # def create_copy_for(approval_id, copy_for_user_id, from_user_id):
        #     """创建抄送"""
        #     copy_for_obj.create({
        #         'approval_id': approval_id,
        #         'model': model,
        #         'res_id': res_id,
        #         'copy_for_user_id': copy_for_user_id,
        #         'from_user_id': from_user_id
        #     })
        #
        # def copy_for(approval):
        #     """创建抄送"""
        #     for copy_for_user_id in self.copy_for_ids:
        #         create_copy_for(approval.id, copy_for_user_id.id, self.env.user.id)
        #
        # def create_approval():
        #     """创建审批信息"""
        #
        #     vals = {
        #         'wait_approval_id': wait_approval.id,
        #         'action_type': action_type,
        #         'idea': self.idea,
        #         'user_id': self.env.user.id
        #     }
        #     if action_type == 'refuse':
        #         vals['refuse_node_id'] = self.return_node.id
        #
        #     approval = approval_obj.create(vals)
        #
        #     if action_type == 'accept' and self.copy_for_ids:
        #         copy_for(approval)
        #
        # def send_message(partner_id, instance_id):
        #     """"""
        #     mail_message_obj.create({
        #         # 'subject': model_name,
        #         'model': model,
        #         'res_id': res_id,
        #         # 'record_name': model_name,
        #         'body': u'<p>有%s需要您审批</p>' % model_name,
        #         'partner_ids': [(6, 0, [partner_id])],  # 收件人
        #         'needaction_partner_ids': [(6, 0, [partner_id])],  # 待处理的业务伙伴
        #         'subtype_id': mail_message_subtype_approval_id,  # 子类型
        #         'message_type': 'notification',  # 类型-通知
        #         'author_id': self.env.user.partner_id.id,
        #         'reply_to': False,
        #         'email_from': False,
        #         # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})],  # 通知
        #     })

        def leader_parent_approval():
            """直属领导审批"""
            # 直属领导审批(当前节点的审批类型是直属领导审批且需直属领导的上级审批)
            if instance_node.node_id.node_id.type == 'leader' and instance_node.node_id.node_id.need_parent_parent:
                if not wait_approval.is_parent:
                    employee = employee_obj.search([('user_id', '=', self.env.user.id)])
                    employee_parent = employee.parent_id # 当前用户的直属领导
                    if employee_parent:
                        user_id = employee_parent.user_id.id # 直属领导的直属领导对应的用户
                        if self.env.user.id != user_id: # 当前用户的直属领导的用户不是当前用户
                            wait_approval_obj.create({
                                'instance_node_id': instance_node_id,
                                'apply_id': self.env.user.id,
                                'user_id': user_id, # 待审批用户
                                'is_parent': True, # 待审批是直属领导的上级或部门领导的上级审批
                                'state': 'running',
                            })
                            partner_id = employee_parent.user_id.sudo().partner_id.id
                            self.send_message(partner_id, model, res_id, model_name, mail_message_subtype_approval_id)
                            return True

        def department_head_parent_approval():
            """部门领导审批"""
            # 部门领导审批(当前节点的审批类型是部门领导审批且需部门领导的上级审批)
            if instance_node.node_id.node_id.type == 'department_head' and instance_node.node_id.node_id.need_department_parent:
                if not wait_approval.is_parent:
                    employee = getattr(document, 'employee_id', False) # 单据的员工字段
                    if employee:
                        department = employee.department_id # 员工的部门
                        parent_department = department.parent_id # 员工的部门的上级部门
                        manager = parent_department.manager_id # 上级部门的管理员
                        user_id = manager.user_id # 上级部门的管理员对应的用户

                        if department and parent_department and manager and user_id:
                            if self.env.user.id != user_id.id:
                                wait_approval_obj.create({
                                    'instance_node_id': instance_node_id,
                                    'apply_id': self.env.user.id,
                                    'user_id': user_id.id,
                                    'is_parent': True,  # 待审批是直属领导的上级或部门领导的上级审批
                                    'state': 'running',
                                })
                                partner_id = user_id.sudo().partner_id.id
                                self.send_message(partner_id, model, res_id, model_name, mail_message_subtype_approval_id)
                                return True

        def check_wait_approval_approvaled(wa):
            """检验待审批用户是否审批过了"""
            if wa.state == 'complete':
                return True

            # 实例节点
            if approval_obj.search([('instance_node_id.instance_id', '=', wa.instance_node_id.instance_id.id), ('user_id', '=', wa.user_id.id), ('action_type', '=', u'accept')]):
                wa.state = 'complete'
                return True

            return False

        def active_next_instance_node(next_instance_node):
            """激活下一步"""
            seam_serial_nodes = instance_node_obj.search([('res_id', '=', res_id), ('model_name', '=', model), ('serial_num', '=', next_instance_node.serial_num), ('instance_id', '=', next_instance_node.instance_id.id)])
            seam_serial_nodes.write({'state': 'running'})
            for wa in wait_approval_obj.search([('instance_node_id', 'in', seam_serial_nodes.ids)]):
                if wa.state == 'complete':
                    continue

                wa.state = 'running'
                partner_id = wa.user_id.sudo().partner_id.id
                self.send_message(partner_id, model, res_id, model_name, mail_message_subtype_approval_id)

        # def approval_done():
        #     """审批完成"""
        #     # instance_node.instance_id.state = 'complete'
        #     res_state.approval_state = 'complete'
        #     approval_flow = res_state.flow_id
        #     # 流程完成执行
        #     if approval_flow.completed_run:
        #         for method in approval_flow.completed_run.split(','):
        #             getattr(document, method.strip())()
        #
        #     # 完成后发送通知
        #     user_ids = []
        #     if approval_flow.complete_copy_for_type == 'user':
        #         user_ids = approval_flow.complete_copy_for_user_ids
        #
        #     if approval_flow.complete_copy_for_type == 'job':
        #         job_ids = approval_flow.complete_copy_for_job_ids.ids
        #         user_ids = [employee.user_id for employee in employee_obj.search([('job_id', 'in', job_ids), ('user_id', '!=', False)])]
        #
        #     if user_ids:
        #         if approval_flow.complete_copy_for_only_document_company:
        #             user_ids = [user.id for user in filter(lambda x: x.company_id.id == document.company_id.id, user_ids)]
        #         else:
        #             user_ids = [user.id for user in user_ids]
        #
        #         for user in users_obj.browse(user_ids):
        #             send_message(user.partner_id.id, False)
        #             self.create_copy_for(False, model, res_id, user.id, self.env.user.id)

        def accept_next_action():
            """同意"""

            # 当前实例节点是否全部审批完成
            wait_approval_count = len(wait_approval_obj.search([('instance_node_id', '=', instance_node_id)])) # 待审批数量
            approval_count = len(approval_obj.search([('wait_approval_id.instance_node_id', '=', instance_node_id)])) # 已审批数量
            if wait_approval_count != approval_count:
                wait_approval.state = 'complete'  # 这里分开写
                return

            # 直属领导审批(当前节点的审批类型是直属领导审批且需直属领导的上级审批)
            if leader_parent_approval():
                wait_approval.state = 'complete'  # 这里分开写
                return

            # 部门领导审批(当前节点的审批类型是部门领导审批且需部门领导的上级审批)
            if department_head_parent_approval():
                wait_approval.state = 'complete'  # 这里分开写
                return

            wait_approval.state = 'complete'  # 这里分开写

            # 节点状态为完成时，执行
            if instance_node.node_id.complete_run:
                for method in instance_node.node_id.complete_run.split(','):
                    getattr(document, method.strip())()

            # 当前顺序的所有节点是否审批完成
            seam_serial_nodes = instance_node_obj.search([('res_id', '=', res_id), ('model_name', '=', model), ('serial_num', '=', instance_node.serial_num), ('instance_id', '=', instance_node.instance_id.id)])
            is_all_done = all([seam_serial_node.state == 'complete' for seam_serial_node in seam_serial_nodes])
            if not is_all_done:
                return

            # 激活下一步
            next_instance_node = None
            for next_node in instance_node_obj.search([('res_id', '=', res_id), ('model_name', '=', model), ('serial_num', '>', instance_node.serial_num), ('instance_id', '=', instance_node.instance_id.id)], order='serial_num asc'):
                # 待审批的都审批了
                wait_approval_all_approvaled = all([check_wait_approval_approvaled(wa) for wa in wait_approval_obj.search([('instance_node_id', '=', next_node.id)])])
                if wait_approval_all_approvaled:
                    next_node.state = 'complete'
                else:
                    if not next_instance_node:
                        next_instance_node = next_node

            if next_instance_node:
                active_next_instance_node(next_instance_node)
            else:
                self.approval_done(res_state, document, model, res_id, model_name, mail_message_subtype_approval_id)

        def refuse_next_action():
            """拒绝"""
            # 未审批完的节点信息
            undone_info = []
            str_node_ids = json.loads(res_state.str_node_ids)
            return_node_serial_num = list(filter(lambda x: x['node_id'] == self.return_node.id, str_node_ids))[0]['serial_num']
            for node_info in str_node_ids:
                if node_info['serial_num'] < return_node_serial_num:
                    continue

                undone_info.append({
                    'node_id': node_info['node_id'],
                    'user_ids': node_info.get('user_ids', ''),
                })

            instance_node.instance_id.undone_info = json.dumps(undone_info)

            # 删除当前节点后的所有实例节点，级联删除wait.approval/approval
            domain = [('instance_id', '=', instance_node.instance_id.id), ('serial_num', '>', instance_node.serial_num)]
            for inode in instance_node_obj.search(domain):
                inode.unlink()

            for wa in wait_approval_obj.search([('instance_node_id.instance_id', '=', instance_node.instance_id.id)]):
                if not approval_obj.search([('wait_approval_id', '=', wa.id)]):
                    wa.unlink()


            # 将当前记录的is_commit_approval(是否提交审批)置为False，等待提交审批
            vals = {'is_commit_approval': False}
            if self.return_node.node_id.is_start:
                vals['approval_state'] = False
            res_state.write(vals)

            wait_approval.state = 'complete' # 这里分开写

            # 驳回到开始节点自动运行审批流程的取消审批自动运行
            if self.return_node.node_id.is_start:
                approval_flow = res_state.flow_id
                if approval_flow.cancel_run:
                    for method in approval_flow.cancel_run.split(','):
                        getattr(document, method.strip())()
            else:
                document.commit_approval()

        def close_mail_channel():
            """关闭沟通的mail.channel"""
            for channel in channel_obj.search([('wait_approval_id', '=', wait_approval.id)]):
                if channel.create_uid.id == self.env.user.id:
                    channel.active = False


        record_approval_state_obj = self.env['record.approval.state']
        instance_node_obj = self.env['approval.flow.instance.node']
        approval_obj = self.env['approval']
        wait_approval_obj = self.env['wait.approval'].sudo()
        # copy_for_obj = self.env['approval.copy_for'].sudo()
        employee_obj = self.env['hr.employee'].sudo()
        # mail_message_obj = self.env['mail.message'].sudo()
        model_obj = self.env['ir.model'].sudo()
        # users_obj = self.env['res.users'].sudo()
        channel_obj = self.env['mail.channel'].sudo()

        # instance_node_id = self._context['instance_node_id']  # 实例节点ID
        res_id = self._context['res_id'] # 记录ID
        model = self._context['res_model'] # 记录model
        action_type = self.action_type # 动作类型
        document = self.env[model].sudo().browse(res_id)  # 当前记录

        model_name = model_obj.search([('model', '=', model)]).name
        mail_message_subtype_approval_id = self.env.ref('web_approval.mail_message_subtype_approval').id
        wait_approval = wait_approval_obj.browse(self._context['wait_approval_id']) # 当前审批对应的待审批
        instance_node = wait_approval.instance_node_id
        instance_node_id = instance_node.id

        res_state = record_approval_state_obj.search([('model', '=', model), ('res_id', '=', res_id)])
        if res_state.approval_state == 'cancel':
            raise ValidationError(u'审批流程取消!')
        if res_state.approval_state == 'pause':
            raise ValidationError(u'审批流程暂停!')

        # 创建审批信息
        self.create_approval(wait_approval, action_type, model, res_id)
        # 关闭沟通的mail.channel
        close_mail_channel()


        # 审批后的下一步动作
        if action_type == 'accept':
            accept_next_action()
        else:
            refuse_next_action()

        return {'type': 'ir.actions.client', 'tag': 'reload', 'state': 1}


