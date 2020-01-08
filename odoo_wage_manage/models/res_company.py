# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    SOCIALSTATE = [
        ('not_done', "未完成"),
        ('just_done', "刚完成"),
        ('done', "完成"),
        ('closed', "关闭")
    ]

    wage_manage_done_state = fields.Selection(SOCIALSTATE, string="社保进度完成情况", default='not_done')

    wage_rule_state = fields.Selection(SOCIALSTATE, string="薪资方案完成情况", default='not_done')
    wage_taxdetail_state = fields.Selection(SOCIALSTATE, string="个税明细完成情况", default='not_done')
    wage_annal_state = fields.Selection(SOCIALSTATE, string="薪资统计完成情况", default='not_done')
    wage_accounting_state = fields.Selection(SOCIALSTATE, string="薪资计算完成情况", default='not_done')

    @api.model
    def action_close_wage_manage_state_onboarding(self):
        """ Mark the onboarding panel as closed. """
        self.env.user.company_id.wage_manage_done_state = 'closed'

    def get_and_update_wage_quotation_onboarding_state(self):
        steps = [
            'wage_rule_state',
            'wage_taxdetail_state',
            'wage_annal_state',
            'wage_accounting_state',
        ]
        return self.get_and_update_onbarding_state('wage_manage_done_state', steps)

    @api.model
    def action_wage_rule_layout(self):
        action = self.env.ref('odoo_wage_manage.action_wage_calculate_salary_rules_layout').read()[0]
        return action

    @api.model
    def action_wage_taxdetail_layout(self):
        action = self.env.ref('odoo_wage_manage.wage_employee_tax_details_action').read()[0]
        return action

    @api.model
    def action_wage_annal_layout(self):
        action = self.env.ref('odoo_wage_manage.wage_employee_attendance_annal_action').read()[0]
        return action

    @api.model
    def action_wage_accounting_layout(self):
        action = self.env.ref('odoo_wage_manage.wage_payroll_accounting_transient_action').read()[0]
        return action