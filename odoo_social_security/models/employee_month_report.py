# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class EmployeeMonthReport(models.Model):
    _name = 'employee.monthly.insured.report'
    _auto = False
    _description = '员工月账单汇总'

    company_id = fields.Many2one('res.company', '公司', )
    employee_id = fields.Many2one(comodel_name='hr.employee', string=u'员工')
    department_id = fields.Many2one(comodel_name='hr.department', string=u'部门')
    monthly_date = fields.Date(string=u'月结日期')
    date_code = fields.Char(string='期间代码')
    personal_sum = fields.Float(string=u'个人社保合计', digits=(10, 2))
    company_sum = fields.Float(string=u'公司社保合计', digits=(10, 2))
    public_personal_sum = fields.Float(string=u'个人公积金合计', digits=(10, 2))
    public_company_sum = fields.Float(string=u'公司公积金合计', digits=(10, 2))

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'employee_monthly_insured_report')
        self.env.cr.execute("""CREATE VIEW employee_monthly_insured_report AS (
            SELECT
                MIN(ims.employee_id) AS id,
                ims.company_id AS company_id,
                ims.employee_id AS employee_id,
                ims.department_id AS department_id,
                ims.monthly_date AS monthly_date,
                ims.date_code AS date_code,
                SUM(ims.personal_sum) AS personal_sum,
                SUM(ims.company_sum) AS company_sum,
                SUM(ims.public_personal_sum) AS public_personal_sum,
                SUM(ims.public_company_sum) AS public_company_sum
            FROM
                insured_monthly_statement AS ims
            GROUP BY
                ims.company_id,ims.date_code,ims.department_id,ims.employee_id,ims.monthly_date
        )""")






