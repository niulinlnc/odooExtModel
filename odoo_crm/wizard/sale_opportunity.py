# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


SALESTATED = [
    ('find', '发现需求'),
    ('confirm', '确认需求'),
    ('solve', '解决方案'),
    ('talk', '商务谈判'),
    ('bid', '招投标'),
    ('win', '赢单'),
    ('losing', '输单'),
    ('cancel', '取消'),
]


class SaleOpportunityState(models.TransientModel):
    _name = 'crm.sale.opportunity.state'
    _description = "机会状态变更"

    state = fields.Selection(string="变更状态", selection=SALESTATED, default='find', required=True)
    note = fields.Text(string="变更原因", required=True)
    opportunity_id = fields.Many2one(comodel_name='crm.sale.opportunity', string="机会", required=True)

    @api.model
    def default_get(self, fields):
        res = super(SaleOpportunityState, self).default_get(fields)
        res['opportunity_id'] = self.env.context.get('active_id')
        return res

    def commit_state(self):
        """
        确认变更状态
        :return:
        """
        self.ensure_one()
        self.opportunity_id.write({'state': self.state})
        note = "变更状态原因：{}".format(self.note)
        self.opportunity_id.message_post(body=note, message_type='notification')
        return {'type': 'ir.actions.act_window_close'}