# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmSaleInvoice(models.Model):
    _name = 'crm.sale.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '销售发票'
    _rec_name = 'code'
    _order = 'id'

    def _default_currency(self):
        """
        获取当前公司默认币种
        :return:
        """
        return self.env.user.company_id.currency_id.id

    INVOICETYPE = [
        ('00', '增值税普通发票'),
        ('01', '增值税专用发票'),
        ('02', '国税通用机打发票'),
        ('03', '地税通用机打发票'),
        ('04', '收据'),
    ]
    INVOICESTATE = [
        ('new', '新的'),
        ('confirm', '已确认'),
        ('void', '作废'),
        ('red', '红冲'),
    ]

    active = fields.Boolean(string=u'Active', default=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True)
    currency_id = fields.Many2one('res.currency', '币种', required=True, default=_default_currency)
    code = fields.Char(string="单据编号", required=True, default='New', track_visibility='onchange', index=True)
    invoice_number = fields.Char(string="发票号码", required=True)
    applicant_id = fields.Many2one(comodel_name="res.users", string="申请人", required=True)
    partner_id = fields.Many2one("res.partner", string="客户", required=True, index=True, track_visibility='onchange')
    contract_id = fields.Many2one(comodel_name="crm.sale.contract", string="合同", domain="[('partner_id','=', partner_id)]")
    cashback_ids = fields.Many2many(comodel_name="sale.contract.cashback.plan", string="关联回款")
    invoice_date = fields.Date(string="开票日期", required=True, default=fields.Date.context_today)
    subtotal = fields.Monetary(string="开票金额", digits=(10, 2))
    invoice_type = fields.Selection(string="发票类型", selection=INVOICETYPE, default='00')
    note = fields.Text(string="备注")
    state = fields.Selection(string="状态", selection=INVOICESTATE, default='new')
    # ---发票信息---
    look_type = fields.Selection(string="抬头类型", selection=[('00', '企业'), ('01', '个人')], default='00')
    invoice_look = fields.Char(string="发票抬头")
    tax_number = fields.Char(string="纳税识别号")
    look_phone = fields.Char(string="注册电话")
    look_addr = fields.Char(string="开票地址")
    look_bank = fields.Char(string="开户行")
    look_bank_number = fields.Char(string="开户账号")
    # ----寄送信息---
    recipient = fields.Char(string="收件人")
    recipient_phone = fields.Char(string="联系电话")
    recipient_postal = fields.Char(string="邮政编码")
    recipient_addr = fields.Char(string="详细地址")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('crm.sale.invoice.code')
        return super(CrmSaleInvoice, self).create(values)