# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BorrowBooksTran(models.TransientModel):
    _name = 'borrow.books.tran'

    book_id = fields.Many2one(comodel_name="odoo.books", string="图书", required=True, index=True, ondelete='cascade')
    borrow_number = fields.Integer(string="数量", required=True, default=1)
    user_id = fields.Many2one(comodel_name="res.users", string="借阅人", default=lambda self: self.env.user.id)
    borrow_time = fields.Datetime(string="借阅时间", required=True, default=fields.Datetime.now)
    return_time = fields.Datetime(string="归还时间")
    notes = fields.Text(string="说明")

    @api.model
    def default_get(self, fields):
        res = super(BorrowBooksTran, self).default_get(fields)
        res['book_id'] = self.env.context.get('active_id')
        return res

    def commit_borrow(self):
        """
        确认借阅
        :return:
        """
        for res in self:
            if res.book_id.remaining_amount < 1:
                raise UserError("该图书已经没有可借阅的数量了，请等待他人归还或管理员采购后再试!")
            if res.borrow_number > res.book_id.remaining_amount:
                raise UserError("您输入的数量不能大于该图书剩余数量：({})！".format(res.book_id.remaining_amount))
            data = {
                'book_id': res.book_id.id,
                'type_id': res.book_id.type_id.id,
                'borrow_number': res.borrow_number,
                'user_id': res.user_id.id,
                'borrow_time': res.borrow_time,
                'return_time': res.return_time,
                'notes': res.notes,
            }
            self.env['book.borrowing.records'].create(data)

