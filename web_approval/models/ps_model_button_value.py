# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.web.controllers.main import DataSet
from odoo.http import request
from odoo import http


class PsModelButtonValue(models.Model):
    _name = 'ps.model.button.value'
    _description = '模型按钮值'
    _rec_name = 'button_string'

    model_id = fields.Many2one('ir.model', string='模型')
    model_model = fields.Char(string='模型名', related='model_id.model', store=True)
    button_name = fields.Char(string='按钮方法')
    button_string = fields.Char(string="按钮显示值")
    button_modifiers = fields.Char(string="按钮属性值")
    is_blacklist = fields.Boolean(string="是否黑名单", default=False)
    is_submit_approval = fields.Boolean(string="是否在审批", default=True)


class PsDataSet(DataSet):

    @http.route('/web/dataset/call_button', type='json', auth="user")
    def call_button(self, model, method, args, domain_id=None, context_id=None):
        # 黑名单中 button
        record = request.env['ps.model.button.value'].search(
            [('model_model', '=', model), ('button_name', '=', method), ('is_blacklist', '=', True)])
        params = args[1].get('params')
        if params:
            res_id = params.get('id')
        else:
            res_id = args[0][0] if args[0] else 0  # 当前单据的id
        if record and res_id:
            # 当前单据的审批状态
            approval_state = request.env['record.approval.state'].search([('model', '=', model), ('res_id', '=', res_id)])
            if approval_state and approval_state.approval_state != 'complete':  # 审批未完成
                raise ValidationError(_('此单据未通过审批，该功能无法使用'))
        return super(PsDataSet, self).call_button(model, method, args, domain_id, context_id)
