# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class PsModelStateFiledValue(models.Model):
    _name = 'ps.model.state.filed.value'
    _description = '模型状态值'
    _rec_name = 'state_display_value'

    model_id = fields.Many2one('ir.model', string='模型')
    state_filed_name = fields.Char(string='状态字段')
    state_value = fields.Char(string="状态值")
    state_display_value = fields.Char(string="状态显示值")
