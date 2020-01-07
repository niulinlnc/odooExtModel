# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReturnBooksTran(models.TransientModel):
    _name = 'return.books.tran'

    record_id = fields.Many2one(comodel_name="book.borrowing.records", string="借阅记录",
                                domain=lambda self: [('user_id', '=', self.env.user.id), ('state', '!=', 'ing')])
    book_id = fields.Many2one(comodel_name="odoo.books", string="图书")
    borrow_number = fields.Integer(string="归还数量", required=True, default=1)
    user_id = fields.Many2one(comodel_name="res.users", string="归还人", default=lambda self: self.env.user.id)
    return_time = fields.Datetime(string="归还时间", default=fields.Datetime.now)
    notes = fields.Text(string="备注")

    @api.onchange('record_id')
    def _onchange_record(self):
        """
        动态获取借阅记录值
        :return:
        """
        for res in self:
            if res.record_id:
                res.book_id = res.record_id.book_id.id
                res.borrow_number = res.record_id.borrow_number - res.record_id.return_number

    def commit_return(self):
        """
        确认借阅
        :return:
        """
        for res in self:
            if res.borrow_number > res.record_id.borrow_number:
                raise UserError("归还数量不能超过借阅的数量!")
            if res.borrow_number < 1:
                raise UserError("警告：归还数量输入不合法！")
            if res.record_id.return_number + res.borrow_number > res.record_id.borrow_number:
                raise UserError("警告：归还数量不正确，总共借阅：{}，已归还：{}".format(res.record_id.borrow_number,res.record_id.return_number))
            res.record_id.write({
                'return_number': res.record_id.return_number + res.borrow_number,
                'return_user': res.user_id.id,
                'return_time': res.return_time,
                'return_notes': res.notes,
            })
