# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class BooksPoolReport(models.Model):
    _name = 'books.pool.report'
    _auto = False
    _description = '借阅汇总'

    company_id = fields.Many2one('res.company', '公司')
    book_id = fields.Many2one(comodel_name="odoo.books", string="图书")
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="类型")
    borrow_time = fields.Datetime(string="借阅时间")
    user_id = fields.Many2one(comodel_name="res.users", string="借阅人")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'books_pool_report')
        self.env.cr.execute("""CREATE VIEW books_pool_report AS (
            SELECT
                MIN(bbr.id) AS id,
                bbr.company_id AS company_id,
                bbr.book_id AS book_id,
                bbr.type_id AS type_id,
                bbr.borrow_time AS borrow_time,
                bbr.user_id AS user_id
            FROM
                book_borrowing_records AS bbr
            GROUP BY
                bbr.company_id, bbr.book_id, bbr.type_id, bbr.borrow_time, bbr.user_id
        )""")

