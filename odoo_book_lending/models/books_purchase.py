# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BooksPurchase(models.Model):
    _description = '图书采购'
    _name = 'odoo.books.purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    PURCHASESTATE = [
        ('draft', '草稿'),
        ('purchase', '采购中'),
        ('confirm', '已完成'),
        ('close', '作废'),
    ]

    name = fields.Char(string="采购标题", required=True, track_visibility='onchange')
    code = fields.Char(string="采购编号", index=True, track_visibility='onchange', default='New')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    user_id = fields.Many2one(comodel_name="res.users", string="采购人", default=lambda self: self.env.user.id)
    purchase_date = fields.Date(string="采购日期", default=fields.Date.context_today)
    state = fields.Selection(string="状态", selection=PURCHASESTATE, default='draft')
    notes = fields.Text(string="备注")
    line_ids = fields.One2many(comodel_name="odoo.books.purchase.line", inverse_name="purchase_id", string="采购列表")
    
    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('odoo.books.purchase.code')
        return super(BooksPurchase, self).create(values)

    def submit_purchase(self):
        """
        确认采购
        :return:
        """
        for res in self:
            res.write({'state': 'purchase'})
            for line in res.line_ids:
                if line.number < 1:
                    raise UserError("采购数量不正确，请纠正！")

    def confirm_purchase(self):
        """
        完成采购，写入图书信息
        :return:
        """
        for res in self:
            res.write({'state': 'confirm'})
            for line in res.line_ids:
                line.book_id.write({
                    'number': line.book_id.number + line.number
                })

    def return_draft(self):
        """
        退回
        :return:
        """
        for res in self:
            res.write({'state': 'draft'})

    def close_apply(self):
        """
        作废
        :return:
        """
        for res in self:
            res.write({'state': 'close'})

    def unlink(self):
        for res in self:
            if res.state != 'draft':
                raise UserError("非草稿单据不允许删除！")
        return super(BooksPurchase, self).unlink()


class BooksPurchaseLine(models.Model):
    _description = '图书采购列表'
    _name = 'odoo.books.purchase.line'
    _rec_name = 'purchase_id'

    purchase_id = fields.Many2one(comodel_name="odoo.books.purchase", string="图书采购", ondelete='set null')
    book_id = fields.Many2one(comodel_name="odoo.books", string="图书名称", required=True)
    code = fields.Char(string="图书编号")
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="图书类型")
    author = fields.Char(string="作者")
    version = fields.Char(string="版本")
    number = fields.Integer(string="数量", default=1)
    price = fields.Float(string="单价(￥)")
    book_time = fields.Datetime(string="预计到货时间")

    @api.onchange('book_id')
    def _onchange_book_id(self):
        """
        :return:
        """
        if self.book_id:
            self.code = self.book_id.code
            self.type_id = self.book_id.type_id.id
            self.author = self.book_id.author
            self.version = self.book_id.version
            self.price = self.book_id.price



