# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmSaleOrderReturn(models.Model):
    _name = 'crm.sale.order.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '退货退款'
    _rec_name = 'code'
    _order = 'id'

    def _default_currency(self):
        """
        获取当前公司默认币种
        :return:
        """
        return self.env.user.company_id.currency_id.id

    active = fields.Boolean(string=u'Active', default=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True)
    currency_id = fields.Many2one('res.currency', '币种', required=True, default=_default_currency)
    name = fields.Char(string="单据名称", required=True, track_visibility='onchange', index=True)
    code = fields.Char(string="单据编号", required=True, default='New', track_visibility='onchange', index=True)
    partner_id = fields.Many2one("res.partner", string="客户", required=True, index=True, track_visibility='onchange')
    contract_id = fields.Many2one(comodel_name="crm.sale.contract", string="订单合同", domain="[('partner_id','=', partner_id)]")
    signatory_id = fields.Many2one("res.users", string="签订人", default=lambda self: self.env.user.id)
    signing_date = fields.Date(string="签订日期", required=True, default=fields.Date.context_today)
    principal_ids = fields.Many2many("res.users", "crm_sale_return_principal_users_rel", string="负责人", required=True)
    collaborator_ids = fields.Many2many("res.users", "crm_sale_return_collaborator_users_rel", string="协同人")
    line_ids = fields.One2many(comodel_name="crm.sale.order.return.line", inverse_name="order_id", string="明细")
    subtotal = fields.Monetary(string="合计金额", digits=(10, 2), store=True, compute='_amount_subtotal')
    note = fields.Text(string="备注")

    @api.onchange('line_ids')
    @api.depends('line_ids')
    def _amount_subtotal(self):
        """
        计算合计合同金额
        """
        for res in self:
            sum_amout = 0
            for line in res.line_ids:
                sum_amout += line.subtotal
            res.subtotal = sum_amout

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('crm.sale.order.return.code')
        return super(CrmSaleOrderReturn, self).create(values)


class CrmSaleOrderReturnLine(models.Model):
    _name = 'crm.sale.order.return.line'
    _description = '退货退款明细'

    def _default_currency(self):
        """
        获取当前公司默认币种
        :return:
        """
        return self.env.user.company_id.currency_id.id

    order_id = fields.Many2one(comodel_name="crm.sale.order.return", string="退货退款单")
    currency_id = fields.Many2one('res.currency', '币种', required=True, default=_default_currency)
    product_id = fields.Many2one(comodel_name="product.template", string="产品", required=True)
    price = fields.Float(string=u'价格', digits=(10, 2), required=True)
    number = fields.Float(string="数量", digits=(10, 2), required=True)
    discount = fields.Float(string="折扣(%)", digits=(10, 2))
    subtotal = fields.Monetary(string="小计", digits=(10, 2), compute='_amount_subtotal')
    return_amout = fields.Monetary(string="退款金额", digits=(10, 2))
    note = fields.Text(string="说明")

    @api.onchange('price', 'number', 'discount')
    def _amount_subtotal(self):
        """
        计算小计
        """
        for res in self:
            if res.discount > 0:
                res.subtotal = res.price * res.number * (res.discount/100)
            else:
                res.subtotal = res.price * res.number

    @api.onchange('product_id')
    def _onchange_product(self):
        """
        获取产品信息
        """
        for res in self:
            if res.product_id:
                res.price = res.product_id.list_price
                res.number = 1.00

