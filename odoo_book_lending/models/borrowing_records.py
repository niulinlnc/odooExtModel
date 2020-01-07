# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BooksBorrowingRecords(models.Model):
    _description = '借还记录'
    _name = 'book.borrowing.records'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    BORROWSTATE = [
        ('out', '已借出'),
        ('oth', '部分归还'),
        ('ing', '已归还')
    ]

    code = fields.Char(string="借阅编号", required=True, default='New', track_visibility='onchange')
    state = fields.Selection(string="借阅状态", selection=BORROWSTATE, store=True, compute='_compute_state')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    book_id = fields.Many2one(comodel_name="odoo.books", string="图书", required=True, index=True, ondelete='cascade', track_visibility='onchange')
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="图书类型", track_visibility='onchange')
    borrow_number = fields.Integer(string="借阅数量", required=True, default=1, track_visibility='onchange')
    return_number = fields.Integer(string="归还数量", track_visibility='onchange')
    user_id = fields.Many2one(comodel_name="res.users", string="借阅人", default=lambda self: self.env.user.id, track_visibility='onchange')
    borrow_time = fields.Datetime(string="借阅时间", required=True, default=fields.Datetime.now, track_visibility='onchange')
    return_user = fields.Many2one(comodel_name="res.users", string="归还人", track_visibility='onchange')
    return_time = fields.Datetime(string="归还时间", track_visibility='onchange')
    notes = fields.Text(string="借阅备注")
    return_notes = fields.Text(string="归还备注")
    apply_id = fields.Many2one(comodel_name="odoo.borrow.apply", string="借阅申请")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('book.borrowing.records.code')
        return super(BooksBorrowingRecords, self).create(values)

    @api.depends('code', 'book_id', 'borrow_number', 'return_number')
    def _compute_state(self):
        """
        自动计算单据状态
        :return:
        """
        for res in self:
            if res.return_number == 0:
                res.state = 'out'
            elif res.return_number < res.borrow_number:
                res.state = 'oth'
            elif res.return_number == res.borrow_number:
                res.state = 'ing'



    


