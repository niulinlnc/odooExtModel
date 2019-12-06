# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsuredMonthlyStatement(models.Model):
    _description = '月结账单'
    _name = 'insured.monthly.statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_code'

    active = fields.Boolean(string=u'Active', default=True)
    name = fields.Char(string='名称')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True, required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string=u'参保员工', required=True, index=True)
    department_id = fields.Many2one(comodel_name='hr.department', string=u'员工部门', index=True)
    monthly_date = fields.Date(string=u'月结日期', required=True)
    date_code = fields.Char(string='期间代码', index=True)
    payment_method = fields.Selection(string=u'缴纳方式', selection=[('company', '公司自缴'), ('other', '其他')], default='company')
    line_ids = fields.One2many('insured.monthly.statement.line', 'statement_id', string=u'社保明细')
    provident_ids = fields.One2many('insured.monthly.provident.line', 'statement_id', string=u'公积金明细')
    personal_sum = fields.Float(string=u'个人缴纳总计', digits=(10, 2), compute='_compute_statement_sum')
    company_sum = fields.Float(string=u'公司缴纳合计', digits=(10, 2), compute='_compute_statement_sum')
    notes = fields.Text(string=u'备注')

    @api.constrains('employee_id', 'monthly_date')
    def _constrains_name(self):
        """
        生成name字段
        :return:
        """
        for res in self:
            if res.employee_id and res.monthly_date:
                res.name = "{}&{}".format(res.employee_id.name, str(res.monthly_date)[:7])

    @api.onchange('monthly_date')
    @api.constrains('monthly_date')
    def _alter_date_code(self):
        """
        根据日期生成期间代码
        :return:
        """
        for res in self:
            if res.monthly_date:
                monthly_date = str(res.monthly_date)
                res.date_code = "{}/{}".format(monthly_date[:4], monthly_date[5:7])

    def _compute_statement_sum(self):
        """
        公司缴纳合计、个人缴纳总计
        :return:
        """
        for res in self:
            personal_sum = company_sum = 0
            for line in res.line_ids:
                company_sum += line.company_pay
                personal_sum += line.pension_pay
            for provident in res.provident_ids:
                company_sum += provident.company_pay
                personal_sum += provident.pension_pay
            res.update({
                'company_sum': company_sum,
                'personal_sum': personal_sum,
            })

    def get_employee_all_list(self):
        """
        返回该对象的社保和公积金列表list
        :return:
        """
        statement_ids = list()
        provident_ids = list()
        for line in self.line_ids:
            statement_ids.append((0, 0, {
                'sequence': line.sequence,
                'insurance_id': line.insurance_id.id,
                'base_number': line.base_number,
                'company_pay': line.company_pay,
                'pension_pay': line.pension_pay,
            }))
        for provident in self.provident_ids:
            provident_ids.append((0, 0, {
                'sequence': provident.sequence,
                'insurance_id': provident.insurance_id.id,
                'base_number': provident.base_number,
                'company_pay': provident.company_pay,
                'pension_pay': provident.pension_pay,
            }))
        return statement_ids, provident_ids


class InsuredMonthlyStatementLine(models.Model):
    _description = '月结社保明细'
    _name = 'insured.monthly.statement.line'

    sequence = fields.Integer(string=u'序号')
    statement_id = fields.Many2one(comodel_name='insured.monthly.statement', string=u'员工月结账单', ondelete='cascade')
    insurance_id = fields.Many2one(comodel_name='insured.scheme.insurance', string=u'社保种类', required=True)
    base_number = fields.Float(string=u'险种基数', digits=(10, 2))
    company_pay = fields.Float(string=u'公司缴纳', digits=(10, 2))
    pension_pay = fields.Float(string=u'个人缴纳', digits=(10, 2))


class InsuredMonthlyProvidentLine(models.Model):
    _description = '月结公积金明细'
    _name = 'insured.monthly.provident.line'

    sequence = fields.Integer(string=u'序号')
    statement_id = fields.Many2one(comodel_name='insured.monthly.statement', string=u'员工月结账单', ondelete='cascade')
    insurance_id = fields.Many2one(comodel_name='provident.fund.kind', string=u'公积金种类', required=True)
    base_number = fields.Float(string=u'基数', digits=(10, 2))
    company_pay = fields.Float(string=u'公司缴纳', digits=(10, 2))
    pension_pay = fields.Float(string=u'个人缴纳', digits=(10, 2))
