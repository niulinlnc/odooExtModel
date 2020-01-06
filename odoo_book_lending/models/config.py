# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BooksTypes(models.Model):
    _description = '图书类型'
    _name = 'odoo.books.type'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    color = fields.Integer(string="Color")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


