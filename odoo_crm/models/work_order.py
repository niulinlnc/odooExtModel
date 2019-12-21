
# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmWorkOrder(models.Model):
    _name = 'crm.work.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '工单管理'
    _rec_name = 'code'
    _order = 'id'

    ORDERSTATE = [
        ('be', '待分配'),
        ('processing', '处理中'),
        ('close', '已关闭'),
    ]

    active = fields.Boolean(string="归档", default=True, track_visibility='onchange')
    code = fields.Char(string="工单编号")
    name = fields.Char(string="工单名称", required=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True, index=True, track_visibility='onchange')
    contact_id = fields.Many2one(comodel_name="crm.contact.users", string="联系人", required=False, domain="[('partner_id','=', partner_id)]")
    opportunity_id = fields.Many2one(comodel_name="crm.sale.opportunity", string="关联机会", domain="[('partner_id','=', partner_id)]")
    contract_id = fields.Many2one(comodel_name="crm.sale.contract", string="关联合同", domain="[('partner_id','=', partner_id)]")
    phone = fields.Char(string="联系电话", required=True)
    address = fields.Char(string="联系地址")
    service_fee = fields.Float(string="服务价格")
    order_date = fields.Date(string="实施时间", default=fields.Date.context_today)
    note = fields.Text(string="备注")
    level = fields.Selection(string="紧急程度", selection=[('00', '普通'), ('01', '紧急'), ('02', '非常紧急')], default='00')
    principal_ids = fields.Many2many("res.users", "work_order_and_res_users_rel", "opportunity_id", 'user_id', string="负责人", required=True)
    collaborator_ids = fields.Many2many("res.users", "work_order_and_res_users_rel", "opportunity_id", 'user_id', string="协同人")
    state = fields.Selection(string="状态", selection=ORDERSTATE, default='be')

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('crm.work.order.code')
        return super(CrmWorkOrder, self).create(values)
