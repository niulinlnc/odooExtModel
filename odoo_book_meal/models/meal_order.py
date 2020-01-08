# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MealOrder(models.Model):
    _description = '订餐'
    _name = 'odoo.meal.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    TimeTypes = [
        ('breakfast', '早餐'), ('lunch', '午餐'), ('dinner', '晚餐')
    ]
    ORDERSTATES = [
        ('draft', '草稿'),
        ('received', '待确认'),
        ('success', '已接收'),
    ]

    active = fields.Boolean(string="归档", default=True)
    code = fields.Char(string="编号", track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id.id)
    user_id = fields.Many2one(comodel_name="res.users", string="订餐人", required=True, track_visibility='onchange')
    department_id = fields.Many2one(comodel_name="hr.department", string="所属部门", required=True, track_visibility='onchange')
    dining_time = fields.Date(string="用餐日期", required=True, default=fields.Date.context_today, track_visibility='onchange')
    time_type = fields.Selection(string="时间段", selection=TimeTypes, required=True, default='lunch', track_visibility='onchange')
    line_ids = fields.One2many(comodel_name="odoo.meal.order.line", inverse_name="order_id", string="列表")
    total = fields.Integer(string="数量", compute='_compute_amount_total')
    amount_total = fields.Float(string="总计", digits=(10, 2), store=True, compute='_compute_amount_total')
    note = fields.Text(string="备注")
    state = fields.Selection(string="状态", selection=ORDERSTATES, default='draft', track_visibility='onchange')
    alerts = fields.Text(compute='_compute_alerts_get', string="消息")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('odoo.meal.order.code')
        return super(MealOrder, self).create(values)

    @api.depends('state')
    def _compute_alerts_get(self):
        """
        get the alerts to display on the order form
        """
        alert_msg = [alert.message for alert in self.env['odoo.meal.alert'].search([]) if alert.display]
        if self.state == 'draft':
            self.alerts = alert_msg and '\n'.join(alert_msg) or False

    @api.depends('line_ids.number', 'line_ids.subtotal')
    def _compute_amount_total(self):
        for res in self:
            number = total = 0
            for line in res.line_ids:
                number += line.number
                total += line.subtotal
            res.total = number
            res.amount_total = total

    def submit_order(self):
        """
        提交订单
        :return:
        """
        for res in self:
            res.write({'state': 'received'})

    def confirm_order(self):
        """
        确认订单
        :return:
        """
        for res in self:
            res.write({'state': 'success'})

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
                raise UserError("非草稿单据不允许删除！")
        return super(MealOrder, self).unlink()


class MealOrderLine(models.Model):
    _name = 'odoo.meal.order.line'
    _description = '订餐列表'
    _rec_name = 'order_id'
    
    order_id = fields.Many2one(comodel_name="odoo.meal.order", string="订单", ondelete="cascade")
    type_id = fields.Many2one(comodel_name="odoo.meal.type", string="种类", required=True)
    product_id = fields.Many2one(comodel_name="odoo.meal.product", string="菜品", required=True, domain="[('type_id', '=', type_id)]")
    number = fields.Integer(string="数量", default=1)
    subtotal = fields.Float(string="小计", digits=(10, 2), store=True, compute='_compute_subtotal')
    note = fields.Char(string="备注(口味)")

    @api.depends('number', 'product_id')
    def _compute_subtotal(self):
        for res in self:
            res.subtotal = res.product_id.price * res.number

