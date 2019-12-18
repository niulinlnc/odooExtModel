# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class OnboardingController(http.Controller):

    @http.route('/wage/wage_manage_onboarding_panel', auth='user', type='json')
    def wage_manage_onboarding_panel(self):
        company = request.env.user.company_id
        if not request.env.user._is_admin() or company.wage_manage_done_state == 'closed':
            return {}
        return {
            'html': request.env.ref('odoo_wage_manage.wage_manage_onboarding_panel').render({
                'company': company,
                'state': company.get_and_update_wage_quotation_onboarding_state()
            })
        }
