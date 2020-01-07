# -*- coding: utf-8 -*-
import base64
import logging
from odoo import api, fields, models
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


class Books(models.Model):
    _description = '图书'
    _name = 'odoo.books'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    def _get_default_image(self):
        default_image_path = get_module_resource('odoo_book_lending', 'static/description', 'icon.png')
        return base64.b64encode(open(default_image_path, 'rb').read())

    active = fields.Boolean(string="归档", default=True)
    name = fields.Char(string="图书名称", required=True, index=True, track_visibility='onchange')
    code = fields.Char(string="图书编号", index=True, track_visibility='onchange', default='New')
    color = fields.Integer(string="Color")
    image = fields.Binary(string="封面图", default=_get_default_image)
    type_id = fields.Many2one(comodel_name="odoo.books.type", string="图书类型", track_visibility='onchange')
    author = fields.Char(string="作者", track_visibility='onchange')
    version = fields.Char(string="版本", track_visibility='onchange')
    number = fields.Integer(string="库存数", default=0, track_visibility='onchange')
    price = fields.Float(string="价格(￥)", digits=(10, 2), track_visibility='onchange')
    user_id = fields.Many2one(comodel_name="res.users", string="负责人")
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    notes = fields.Text(string="描述")
    remaining_amount = fields.Integer(string="剩余数量", compute='compute_amount')
    record_ids = fields.One2many(comodel_name="book.borrowing.records", inverse_name="book_id", string="借阅记录")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('odoo.books.code')
        return super(Books, self).create(values)

    def compute_amount(self):
        """
        计算剩余数量
        :return:
        """
        for res in self:
            borrow_num = 0
            return_num = 0
            for record in res.record_ids:
                borrow_num += record.borrow_number
                return_num += record.return_number
            res.remaining_amount = res.number - borrow_num + return_num

    def action_borrow_apply_from(self):
        """
        借阅图书申请
        :return:
        """
        self.ensure_one()
        result = self.env.ref('odoo_book_lending.odoo_borrow_apply_action').read()[0]
        line_list = list()
        line_list.append({
            'book_id': self.id,
            'code': self.code,
            'type_id': self.type_id.id,
            'number': 1,
        })
        result['context'] = {
            'default_name': '{}的借阅申请'.format(self.env.user.name),
            'default_line_ids': line_list,
        }
        res = self.env.ref('odoo_book_lending.odoo_borrow_apply_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result
