# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BooksApply(models.Model):
    _description = '图书申请'
    _name = 'odoo.books.apply'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    APPLYSTATE = [
        ('draft', '草稿'),
        ('confirm', '管理确认'),
        ('purchase', '申请完成'),
        ('close', '作废'),
    ]

    name = fields.Char(string="申请标题", required=True, track_visibility='onchange')
    code = fields.Char(string="申请编号", index=True, track_visibility='onchange', default='New')
    book_name = fields.Char(string="图书名称", required=True, track_visibility='onchange')
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="图书类型", track_visibility='onchange')
    author = fields.Char(string="作者", track_visibility='onchange')
    version = fields.Char(string="版本", track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    description = fields.Text(string="图书描述")
    notes = fields.Text(string="申请原因")
    user_id = fields.Many2one(comodel_name="res.users", string="申请人", required=True, default=lambda self: self.env.user.id)
    apply_date = fields.Date(string="申请日期", required=True, default=fields.Date.context_today)
    state = fields.Selection(string="状态", selection=APPLYSTATE, default='draft', track_visibility='onchange')
    purchase_id = fields.Many2one(comodel_name="odoo.books.purchase", string="图书采购单")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('odoo.books.apply.code')
        return super(BooksApply, self).create(values)

    def confirm_apply(self):
        """
        提交申请
        :return:
        """
        for res in self:
            res.write({'state': 'confirm'})

    def confirm_purchase(self):
        """
        确认采购
        生成采购单并进行关联
        :return:
        """
        for res in self:
            # 创建图书
            book = self.env['odoo.books'].create({
                'name': res.book_name,
                'type_id': res.type_id.id,
                'author': res.author,
                'version': res.version,
                'notes': res.description,
            })
            # 创建采购单
            line_list = list()
            line_list.append((0, 0, {
                'book_id': book.id,
                'code': book.code,
                'type_id': res.type_id.id,
                'author': res.author,
                'version': res.version,
            }))
            data = {
                'name': "《{}》-采购单".format(res.book_name),
                'user_id': self.env.user.id,
                'line_ids': line_list,
            }
            purchase = self.env['odoo.books.purchase'].create(data)
            res.write({'state': 'purchase', 'purchase_id': purchase.id})

    def return_draft(self):
        """
        退回草稿
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
                raise UserWarning("非草稿单据不允许删除！")
        return super(BooksApply, self).unlink()
