# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ApprovalIncreaseWizard(models.TransientModel):
    _name = 'approval.increase.wizard'
    _description = u'加签向导'

    user_id = fields.Many2one('res.users', u'加签审批人', domain="[('share','=',False)]")
    increase_type = fields.Many2one('increase.type', u'加签类型')

    @api.onchange('increase_type')
    def increase_type_changed(self):
        pass

    @api.multi
    def onchange(self, values, field_name, field_onchange):
        wait_approval_obj = self.env['wait.approval']

        increase_type_domain = []

        wait_approval = wait_approval_obj.browse(self._context['wait_approval_id'])
        node = wait_approval.instance_node_id.node_id

        before_increase_id = self.env.ref('web_approval.increase_type_before').id
        after_increase_id = self.env.ref('web_approval.increase_type_after').id

        if node.allow_before_increase:
            if not wait_approval.child_ids.filtered(lambda x: x.increase_type == 'before'):
                increase_type_domain.append(before_increase_id)

        if node.allow_after_increase:
            if not wait_approval.child_ids.filtered(lambda x: x.increase_type == 'after'):
                increase_type_domain.append(after_increase_id)

        result = {
            'domain': {
                'user_id': [('share','=',False), ('id', '!=', self.env.user.id)],
                'increase_type': [('id', 'in', increase_type_domain)]
            },
        }
        if len(increase_type_domain) == 1:
            result.update({
                'value': {
                    'increase_type': increase_type_domain[0]
                }
            })
        return result

    @api.multi
    def button_ok(self):

        instance_node_obj = self.env['approval.flow.instance.node']
        wait_approval_obj = self.env['wait.approval']
        mail_message_obj = self.env['mail.message'].sudo()
        model_obj = self.env['ir.model'].sudo()

        context = self._context
        action_type = self.increase_type.code # 值：before、after，前加签还是后加签
        wait_approval_id = context['wait_approval_id'] # 加签的待审批节点

        wait_approval = wait_approval_obj.browse(wait_approval_id)
        model = wait_approval.model_name
        res_id = wait_approval.res_id

        current_serial_num = wait_approval.serial_num
        if action_type == 'before':
            serial_num = current_serial_num - 1
        else:
            serial_num = current_serial_num + 1

        instance_node = instance_node_obj.create({
            'flow_id': wait_approval.instance_node_id.flow_id.id,
            'node_id': wait_approval.instance_node_id.node_id.id,
            'instance_id': wait_approval.instance_node_id.instance_id.id,
            'serial_num': serial_num,
            'state': 'running' if action_type == 'before' else 'active', # [('active', u'草稿'), ('running', u'正在审批'), ('complete', u'完成')]
        })

        wait_approval_obj.create({
            'instance_node_id': instance_node.id,
            'apply_id': self.env.user.id,  # 申请人
            'user_id': self.user_id.id,  # 待审批用户
            'state': 'running' if action_type == 'before' else 'active',
            # 加签相关
            'is_increase': True,
            'parent_id': wait_approval_id,
            'increase_type': action_type,
        })
        if action_type == 'before':
            # 更新待审批状态
            instance_nodes = instance_node_obj.search([('instance_id', '=', wait_approval.instance_node_id.instance_id.id), ('serial_num', '=', current_serial_num)])
            instance_nodes.write({'state': 'active'})
            wait_approvals = wait_approval_obj.search([('instance_node_id', 'in', instance_nodes.ids)])  # 实例节点对应的待审批
            wait_approvals.write({'state': 'active'})

            mail_message_subtype_approval_id = self.env.ref('web_approval.mail_message_subtype_approval').id
            # 删除通知
            # mail_message_obj.search([('model', '=', model), ('res_id', '=', res_id), ('subtype_id', '=', mail_message_subtype_approval_id)]).unlink()

            # 发送通知
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
                # 'notification_ids': [(0, 0, {'is_email': False, 'res_partner_id': partner_id})], # 通知
                # 'instance_node_id': wait_approval.instance_node_id.id # TODO
            })








        return {
            'state': 1
        }



