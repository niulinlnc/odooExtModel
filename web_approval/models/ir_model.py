# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import ValidationError, UserError


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_approve = fields.Boolean(string="是否配置审批流", default=False)

    @api.multi
    def unlink(self):
        """module卸载model删除时，删除关联的记录审批状态和审批信息"""
        record_approval_state_obj = self.env.get('record.approval.state')
        if record_approval_state_obj is None:
            return super(IrModel, self).unlink()

        instance_obj = self.env['approval.flow.instance'] # .with_context(approval_callback=1)
        # record_approval_state_obj = record_approval_state_obj.with_context(approval_callback=1)


        for model in self:
            record_approval_state_obj.search([('model_name', '=', model.model)]).unlink()
            # 删除审批实例
            instance_obj.search([('model_name', '=', model.model)]).unlink()

        return super(IrModel, self).unlink()




