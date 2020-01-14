# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ApprovalTurnToWizard(models.TransientModel):
    _name = 'approval.turn.to.wizard'
    _description = u'代签向导'

    user_id = fields.Many2one('res.users', u'代签审批人')
    current_uid = fields.Integer('')
    idea = fields.Text(u'代签意见')

    @api.model
    def default_get(self, fields_list):
        res = super(ApprovalTurnToWizard, self.sudo()).default_get(fields_list)
        res['current_uid'] = self.env.user.id
        return res

    @api.multi
    def button_ok(self):
        def create_approval():
            """创建审批信息"""
            vals = {
                'wait_approval_id': wait_approval.id,
                'action_type': 'turn_to',
                'idea': self.idea,
                'user_id': self.env.user.id,
                'turn_to_user_id': self.user_id.id
            }
            approval_obj.create(vals)

        def send_message():
            model_name = model_obj.search([('model', '=', model)]).name
            partner_id = self.user_id.sudo().partner_id.id
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
                # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})],  # 通知
                # 'instance_node_id': wait_approval.instance_node_id.id # TODO
            })

        wait_approval_obj = self.env['wait.approval'].sudo()
        approval_obj = self.env['approval']
        model_obj = self.env['ir.model'].sudo()
        mail_message_obj = self.env['mail.message'].sudo()

        wait_approval_id = self._context['wait_approval_id']  # 待审批ID
        res_id = self._context['res_id']  # 记录ID
        model = self._context['res_model']  # 记录model
        mail_message_subtype_approval_id = self.env.ref('web_approval.mail_message_subtype_approval').id

        wait_approval = wait_approval_obj.browse(wait_approval_id)  # 当前审批对应的待审批

        # 创建审批信息
        create_approval()

        # 创建新的待审批
        wa = wait_approval_obj.create({
            'instance_node_id': wait_approval.instance_node_id.id,
            'apply_id': self.env.user.id,  # 申请人
            'user_id': self.user_id.id,  # 待审批用户
            'state': wait_approval.state,
            'is_turn_to': True
        })
        # 发送系统通知
        if wait_approval.state == 'running':
            send_message()

        # 更新待审批状态
        wait_approval.write({
            'state': 'complete',
            'turn_to_user_id': self.user_id.id
        })

        return {
            'state': True
        }
