# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError
from lxml import etree


class PsIrModelApprove(models.Model):
    _name = 'ps.ir.model.approve'

    name = fields.Char(string='Name', default='模型配置')
    ir_model_ids = fields.Many2many('ir.model', string='模型', domain=[('model','!=','res.partner')])

    state = fields.Selection([('draft', '草稿'), ('confirm', '确认')], default='draft', string="状态")

    def confirm_model_approve(self):
        # models_approve = self.search([('id', '!=', self.id)])
        # for model_approve in models_approve:
        #     if model_approve.state == 'confirm':
        #         raise ValidationError('已经存在确认过的模型配置！')
        self.state = 'confirm'
        for ir_model in self.ir_model_ids:
            ir_model.is_approve = True
            # 模型状态值 表 中添加数据
            # for value in self.env[ir_model.model].fields_get(['state'])['state']['selection']:
            #     self.env['ps.model.state.filed.value'].create({
            #         'model_id': ir_model.id,
            #         'state_filed_name': 'state',
            #         'state_value': value[0],
            #         'state_display_value': value[1]
            #     })

            # 模型按钮值 表 中添加数据
            result = self.env[ir_model.model].fields_view_get()
            root = etree.fromstring(result['arch'])
            for item in root.xpath("//header/button"):
                self.env['ps.model.button.value'].create({
                    'model_id': ir_model.id,
                    'button_name': item.get('name'),
                    'button_string': item.get('string'),
                    'button_modifiers': item.get('modifiers')
                })
            result['arch'] = etree.tostring(root)

    def draft_model_approve(self):
        if self.env['approval.flow'].search([('model_id', 'in', self.ir_model_ids.ids)]):
            raise ValidationError(_('模型已经在审批流程中使用，不能设草稿。'))
        # 删除 模型状态值 表 中数据
        # self.env['ps.model.state.filed.value'].search([('model_id', 'in', self.ir_model_ids.ids)]).unlink()
        # 删除 模型按钮值 表 中数据
        self.env['ps.model.button.value'].search([('model_id', 'in', self.ir_model_ids.ids)]).unlink()
        for ir_model in self.ir_model_ids:
            ir_model.is_approve = False
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state == 'confirm':
                raise ValidationError('确认状态的模型配置不允许删除！')
        res = super(PsIrModelApprove, self).unlink()
        return res

    @api.onchange('ir_model_ids')
    def onchange_ir_model_ids(self):
        for model_approve_id in self.search([]):
            if model_approve_id.state == 'confirm':
                for id in self.ir_model_ids.ids:
                    if id in model_approve_id.ir_model_ids.ids:
                        raise ValidationError('已经存在确认过的模型配置！')

    # @api.multi
    # def write(self, vals):
    #     if self.state == 'confirm':
    #         raise ValidationError('确认状态不允许修改！')
    #     return super(PsIrModelApprove, self).write(vals)
