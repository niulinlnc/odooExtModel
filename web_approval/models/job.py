# -*- coding: utf-8 -*-
from odoo import models, api, fields


class Job(models.Model):
    _inherit = 'hr.job'

    user_names = fields.Char(u'用户', compute='_compute_job_users')

    def _compute_job_users(self):
        employee_obj = self.env['hr.employee'].sudo()
        for job in self:
            user_names = u','.join([u'%s+%s' % (employee.user_id.company_id.name, employee.user_id.name) for employee in employee_obj.search([('job_id', '=', job.id), ('user_id', '!=', False)])])
            job.user_names = user_names







