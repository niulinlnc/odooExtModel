# -*- coding: utf-8 -*-
import base64
import logging
from odoo import api, fields, models
from odoo.modules import get_module_resource

_logger = logging.getLogger(__name__)


class MealProduct(models.Model):
    _description = '菜品'
    _name = 'odoo.meal.product'
    _rec_name = 'name'

    def _get_default_image(self):
        default_image_path = get_module_resource('odoo_book_meal', 'static/description', 'meal_image.png')
        return base64.b64encode(open(default_image_path, 'rb').read())

    active = fields.Boolean(string="归档", default=True)
    name = fields.Char(string="名称", required=True)
    type_id = fields.Many2one(comodel_name="odoo.meal.type", string="种类", required=True)
    code = fields.Char(string="编号", index=True, default='New')
    color = fields.Integer(string="Color")
    image = fields.Binary(string="图像", default=_get_default_image)
    partner_id = fields.Many2one(comodel_name="res.partner", string="供应商")
    price = fields.Float(string="价格", digits=(10, 2))
    notes = fields.Text(string="说明")
    tag_ids = fields.Many2many("odoo.meal.tag", "meal_product_and_tag_rel", "product_id", "tag_id", string="标签")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('meal.product.code')
        return super(MealProduct, self).create(values)



