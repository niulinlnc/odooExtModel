# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MealType(models.Model):
    _description = '菜品类型'
    _name = 'odoo.meal.type'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    color = fields.Integer(string="Color")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class MealTag(models.Model):
    _name = 'odoo.meal.tag'

    name = fields.Char(string="标签名", required=True, index=True)
    color = fields.Integer(string="Color")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]

