# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AddNodeActionWizard(models.TransientModel):
    _name = 'add.node.action.wizard'
    _description = u'添加动作向导'

    flow_id = fields.Many2one('approval.flow', u'流程', ondelete='cascade')
    condition = fields.Char(u'条件')
    source_node_id = fields.Many2one('approval.flow.node', u'源节点')
    target_node_id = fields.Many2one('approval.flow.node', u'目标节点')


    @api.model
    def default_get(self, fields_list):
        res = super(AddNodeActionWizard, self.sudo()).default_get(fields_list)
        context = self._context
        res['source_node_id'] = context['from']
        res['target_node_id'] = context['to']
        res['flow_id'] = context['flow_id']

        return res


    @api.multi
    def button_ok(self):
        self.ensure_one()
        node_action_obj = self.env['approval.flow.node.action']

        context = self._context
        source_node_id = context['from']
        target_node_id = context['to']
        flow_id = context['flow_id']

        # 创建动作
        node_action_obj.create({
            'flow_id': flow_id,
            'source_node_id': source_node_id,
            'target_node_id': target_node_id,
            'condition': self.condition,
        })
        return {
            'state': 1,
        }
