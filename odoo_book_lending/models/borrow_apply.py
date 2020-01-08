# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BorrowApply(models.Model):
    _description = '借阅申请'
    _name = 'odoo.borrow.apply'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    APPLYSTATE = [
        ('draft', '草稿'),
        ('confirm', '管理确认'),
        ('ok', '已批准'),
        ('close', '取消'),
    ]

    name = fields.Char(string="借阅标题", required=True, track_visibility='onchange')
    code = fields.Char(string="借阅编号", index=True, track_visibility='onchange', default='New')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    user_id = fields.Many2one(comodel_name="res.users", string="借阅人", required=True, default=lambda self: self.env.user.id)
    apply_time = fields.Datetime(string="借阅时间", default=fields.Datetime.now, track_visibility='onchange')
    notes = fields.Text(string="借阅说明")
    state = fields.Selection(string="状态", selection=APPLYSTATE, default='draft', track_visibility='onchange')
    line_ids = fields.One2many(comodel_name="odoo.borrow.apply.line", inverse_name="apply_id", string="申请列表")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('odoo.borrow.apply.code')
        return super(BorrowApply, self).create(values)

    def submit_apply(self):
        """
        提交申请单
        :return:
        """
        for res in self:
            for line in res.line_ids:
                if line.book_id.remaining_amount < 1:
                    raise UserError("{}已经没有可借阅的数量了，请等待他人归还或管理员采购后再试!".format(line.book_id.name))
                if line.number > line.book_id.remaining_amount:
                    raise UserError("您输入的数量不能大于该图书({})剩余数量：({})！".format(line.book_id.name, line.book_id.remaining_amount))
            res.write({'state': 'confirm'})

    def confirm_applye(self):
        """
        确认申请
        :return:
        """
        for res in self:
            for line in res.line_ids:
                if line.book_id.remaining_amount < 1:
                    raise UserError("{}已经没有可借阅的数量了，请等待他人归还或管理员采购后再试!".format(line.book_id.name))
                if line.number > line.book_id.remaining_amount:
                    raise UserError("您输入的数量不能大于该图书({})剩余数量：({})！".format(line.book_id.name, line.book_id.remaining_amount))
            res.write({'state': 'ok'})
            # 创建借阅记录
            for line in res.line_ids:
                self.env['book.borrowing.records'].create({
                    'book_id': line.book_id.id,
                    'type_id': line.book_id.type_id.id,
                    'borrow_number': line.number,
                    'user_id': res.user_id.id,
                    'borrow_time': res.apply_time,
                    'return_time': line.return_time,
                    'notes': line.note,
                    'apply_id': res.id,
                })

    def close_apply(self):
        """
        取消申请
        :return:
        """
        for res in self:
            res.write({'state': 'close'})

    def return_draft(self):
        """
        退回草稿
        :return:
        """
        for res in self:
            res.write({'state': 'draft'})

    def unlink(self):
        for res in self:
            if res.state != 'draft':
                raise UserWarning("非草稿单据不允许删除！")
        return super(BorrowApply, self).unlink()


class BorrowApplyLine(models.Model):
    _name = 'odoo.borrow.apply.line'
    _description = '借阅申请列表'
    _rec_name = 'apply_id'
    
    apply_id = fields.Many2one(comodel_name="odoo.borrow.apply", string="借阅申请", ondelete='set null')
    book_id = fields.Many2one(comodel_name="odoo.books", string="图书名称", required=True)
    code = fields.Char(string="图书编号")
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="图书类型")
    number = fields.Integer(string="借阅数量", default=1)
    return_time = fields.Datetime(string="还书时间")
    note = fields.Text(string="借阅说明")

    @api.onchange('book_id')
    def _onchange_book_id(self):
        """
        :return:
        """
        if self.book_id:
            self.code = self.book_id.code
            self.type_id = self.book_id.type_id.id


