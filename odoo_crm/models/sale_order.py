# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SALESTATE = [
    ('offer', '报价中'),
    ('lapse', '失效单'),
    ('contract', '已生成合同'),
]


class SaleOrder(models.Model):
    _name = 'crm.sale.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '报价单'
    _rec_name = 'code'
    _order = 'id'

    def _default_currency(self):
        """
        获取当前公司默认币种
        :return:
        """
        return self.env.user.company_id.currency_id.id

    active = fields.Boolean(string=u'Active', default=True)
    color = fields.Integer(string="Color")
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True)
    currency_id = fields.Many2one('res.currency', '币种', required=True, default=_default_currency)
    name = fields.Char(string="报价名称", required=True, track_visibility='onchange', index=True)
    code = fields.Char(string="报价编号", required=True, default='New', track_visibility='onchange', index=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True, index=True, track_visibility='onchange')
    contact_ids = fields.Many2many(comodel_name="crm.contact.users", string="联系人", domain="[('partner_id','=', partner_id)]")
    opportunity_ids = fields.Many2many(comodel_name="crm.sale.opportunity", string="关联机会", domain="[('partner_id','=', partner_id)]")
    quote_id = fields.Many2one(comodel_name="res.users", string="报价人", required=True, track_visibility='onchange', default=lambda self: self.env.user.id)
    quote_date = fields.Date(string="报价日期", required=True, default=fields.Date.context_today, track_visibility='onchange')
    effective_date = fields.Date(string="有效日期", default=fields.Date.context_today, track_visibility='onchange')
    principal_ids = fields.Many2many("res.users", "crm_sale_order_and_res_users_rel", string="负责人", required=True)
    collaborator_ids = fields.Many2many("res.users", "crm_sale_order_and_res_users_rel", string="协同人")
    line_ids = fields.One2many(comodel_name="crm.sale.order.line", inverse_name="order_id", string="明细行")
    state = fields.Selection(string="状态", selection=SALESTATE, default='offer')

    discounted_price = fields.Monetary(string="优惠金额", digits=(10, 2), track_visibility='onchange')
    subtotal = fields.Monetary(string="报价金额", digits=(10, 2), store=True, compute='_amount_subtotal')
    note = fields.Text(string="备注")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('crm.sale.order.code')
        return super(SaleOrder, self).create(values)

    @api.onchange('line_ids', 'discounted_price')
    @api.depends('line_ids', 'discounted_price')
    def _amount_subtotal(self):
        """
        计算合计报价金额
        """
        for res in self:
            sum_amout = 0
            for line in res.line_ids:
                sum_amout += line.subtotal
            res.subtotal = sum_amout-res.discounted_price

    def to_create_contract(self):
        self.write({'state': 'contract'})

    def return_sale_order(self):
        """
        退回报价单
        :return:
        """
        self.write({'state': 'offer'})

    def create_contract(self):
        """
        创建合同
        :return:
        """
        result = self.env.ref('odoo_crm.crm_sale_contract_action').read()[0]
        result['context'] = {
            'default_name': "%s的合同" % self.partner_id.name,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_ids': [(6, 0, [self.id])],
            'default_order_ids': [(6, 0, [self.id])]
        }
        res = self.env.ref('odoo_crm.crm_sale_contract_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result

    def action_sale_contract(self):
        """
        跳转到合同
        :return:
        """
        result = self.env.ref('odoo_crm.crm_sale_contract_action').read()[0]
        result['context'] = {
            'default_name': "%s的合同" % self.partner_id.name,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_ids': [(6, 0, [self.id])],
            'default_order_ids': [(6, 0, [self.id])]
        }
        result['domain'] = "[('partner_id', '=', %s)]" % (self.partner_id.id)
        return result

    def order_expired(self):
        """
        修改订单为失效
        :return:
        """
        self.write({'state': 'lapse'})


class SaleOrderLine(models.Model):
    _name = 'crm.sale.order.line'
    _description = '报价单明细'
    _rec_name = 'order_id'
    _order = 'id'

    def _default_currency(self):
        """
        获取当前公司默认币种
        :return:
        """
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency', '币种', required=True, default=_default_currency)
    order_id = fields.Many2one(comodel_name="crm.sale.order", string="报价单")
    product_id = fields.Many2one(comodel_name="product.template", string="产品", required=True)
    price = fields.Float(string=u'价格', digits=(10, 2), required=True)
    number = fields.Float(string="数量", digits=(10, 2), required=True)
    discount = fields.Float(string="折扣(%)", digits=(10, 2))
    subtotal = fields.Monetary(string="小计", digits=(10, 2), compute='_amount_subtotal')

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



