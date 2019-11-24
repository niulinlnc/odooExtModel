# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsuredSchemeEmployee(models.Model):
    _description = '参保员工'
    _name = 'insured.scheme.employee'
    _rec_name = 'employee_id'
    _order = 'id'

    active = fields.Boolean(string=u'Active', default=True)
    payment_method = fields.Selection(string=u'缴纳方式', selection=[('company', '公司自缴'), ('other', '其他'), ], default='company')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True, required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string=u'参保员工', index=True, copy=False)
    department_id = fields.Many2one(comodel_name='hr.department', string=u'所属部门', index=True, copy=False)
    scheme_id = fields.Many2one(comodel_name='insured.scheme', string=u'参保方案')
    social_security_start_date = fields.Date(string=u'社保起始日期')
    public_fund_start_date = fields.Date(string=u'公积金起始日期')
    notes = fields.Text(string=u'备注')
    state = fields.Selection(string=u'状态', selection=[('normal', '正常'), ('pause', '暂停'),  ('close', '关闭')], default='normal')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for res in self:
            if res.employee_id:
                res.department_id = res.employee_id.department_id.id

    @api.constrains('employee_id')
    def _constrains_employee(self):
        for res in self:
            emp_count = self.search_count([('employee_id', '=', res.employee_id.id)])
            if emp_count > 1:
                raise UserError(_("该员工已是参保状态"))

    def state_to_pause(self):
        for res in self:
            res.state = 'pause'

    def state_to_normal(self):
        for res in self:
            res.state = 'normal'

    def state_to_close(self):
        for res in self:
            res.state = 'close'

