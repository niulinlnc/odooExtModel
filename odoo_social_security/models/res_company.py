# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    # sale quotation onboarding
    SOCIALSTATE = [
        ('not_done', "未完成"),
        ('just_done', "刚完成"),
        ('done', "完成"),
        ('closed', "关闭")
    ]

    insured_scheme_done_state = fields.Selection(SOCIALSTATE, string="社保进度完成情况", default='not_done')

    insured_scheme_state = fields.Selection(SOCIALSTATE, string="参保方案完成情况", default='not_done')
    insured_scheme_emp_state = fields.Selection(SOCIALSTATE, string="参保员工完成情况", default='not_done')
    insured_month_scheme_state = fields.Selection(SOCIALSTATE, string="月结账单完成情况", default='not_done')
    insured_month_report_scheme_state = fields.Selection(SOCIALSTATE, string="月结报表完成情况", default='not_done')

    @api.model
    def action_close_insured_scheme_state_onboarding(self):
        """ Mark the onboarding panel as closed. """
        self.env.user.company_id.insured_scheme_done_state = 'closed'

    def get_and_update_social_quotation_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = [
            'insured_scheme_state',
            'insured_scheme_emp_state',
            'insured_month_scheme_state',
            'insured_month_report_scheme_state',
        ]
        return self.get_and_update_onbarding_state('insured_scheme_done_state', steps)

    @api.model
    def action_insured_scheme_layout(self):
        """
        调转到参保方案
        """
        self.set_onboarding_step_done('insured_scheme_state')
        action = self.env.ref('odoo_social_security.action_insured_scheme_layout').read()[0]
        return action

    @api.model
    def action_insured_scheme_employee_layout(self):
        action = self.env.ref('odoo_social_security.action_insured_scheme_employee_layout').read()[0]
        return action

    @api.model
    def action_insured_monthly_statement_layout(self):
        action = self.env.ref('odoo_social_security.action_insured_monthly_statement_layout').read()[0]
        return action

    @api.model
    def action_insured_monthly_report_layout(self):
        action = self.env.ref('odoo_social_security.action_insured_monthly_report_layout').read()[0]
        return action