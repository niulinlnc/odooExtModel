# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ComputeInsuredMonthlyStatement(models.TransientModel):
    _name = 'compute.insured.monthly.statement'
    _description = "生成月结账单"

    monthly_date = fields.Date(string=u'月结日期', required=True, default=fields.date.today())
    date_code = fields.Char(string='期间代码')
    emp_ids = fields.Many2many('insured.scheme.employee', string=u'月结员工')

    @api.multi
    def compute_emp_detail(self):
        """
        生成月结账单
        :return:
        """
        self.ensure_one()
        date_code = "{}/{}".format(str(self.monthly_date)[:4], str(self.monthly_date)[5:7])
        insureds = self.env['insured.scheme.employee'].search([('state', '=', 'normal'), ('active', '=', True)])
        for insured in insureds:
            logging.info(">>>生成员工：'%s' 的月结账单" % insured.employee_id.name)
            monthly_data = {
                'employee_id': insured.employee_id.id,
                'department_id': insured.department_id.id,
                'payment_method': insured.payment_method,
                'monthly_date': str(self.monthly_date),
                'date_code': date_code,
            }
            monthly_line = list()
            provident_line = list()
            # 参保方案
            scheme = insured.scheme_id
            # 社保
            for scheme_line in scheme.line_ids:
                if scheme_line.ttype == 'base':
                    monthly_line.append((0, 0, {
                        'insurance_id': scheme_line.insurance_id.id,
                        'base_number': scheme_line.base_number,
                        'company_pay': scheme_line.base_number * scheme_line.company_number,
                        'pension_pay': scheme_line.base_number * scheme_line.personal_number,
                    }))
                else:
                    monthly_line.append((0, 0, {
                        'insurance_id': scheme_line.insurance_id.id,
                        'base_number': scheme_line.base_number,
                        'company_pay': scheme_line.company_fixed_number,
                        'pension_pay': scheme_line.personal_fixed_number,
                    }))
            # 公积金
            for scheme_line in scheme.provident_ids:
                if scheme_line.ttype == 'base':
                    provident_line.append((0, 0, {
                        'insurance_id': scheme_line.insurance_id.id,
                        'base_number': scheme_line.base_number,
                        'company_pay': scheme_line.base_number * scheme_line.company_number,
                        'pension_pay': scheme_line.base_number * scheme_line.personal_number,
                    }))
                else:
                    provident_line.append((0, 0, {
                        'insurance_id': scheme_line.insurance_id.id,
                        'base_number': scheme_line.base_number,
                        'company_pay': scheme_line.company_fixed_number,
                        'pension_pay': scheme_line.personal_fixed_number,
                    }))
            monthly_data.update({'line_ids': monthly_line, 'provident_ids': provident_line})
            # 创建月结账单
            domain = [('employee_id', '=', insured.employee_id.id), ('date_code', '=', date_code)]
            statement = self.env['insured.monthly.statement'].search(domain)
            if statement:
                statement.write({'line_ids': [(2, statement.line_ids.ids)], 'provident_ids': [(2, statement.provident_ids.ids)]})
                statement.write(monthly_data)
            else:
                self.env['insured.monthly.statement'].create(monthly_data)
        logging.info(">>>End生成员工月结账单")
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('monthly_date')
    def _onchagnge_monthly_date(self):
        """
        生成期间代码
        :return:
        """
        if self.monthly_date:
            self.date_code = "{}/{}".format(str(self.monthly_date)[:4], str(self.monthly_date)[5:7])

