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


class ResPartnerReturnStated(models.TransientModel):
    _name = 'res.partner.return.stated'
    _description = "客户阶段变更"

    CUSTOMERSTATED = [
        ('find', '发现需求'),
        ('confirm', '确认需求'),
        ('solve', '解决方案'),
        ('talk', '商务谈判'),
        ('bid', '招投标'),
        ('clinch', '成交'),
    ]

    c_stated = fields.Selection(string="变更阶段", selection=CUSTOMERSTATED, default='find', required=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True)
    note = fields.Text(string="变更原因", required=True)

    @api.model
    def default_get(self, fields):
        res = super(ResPartnerReturnStated, self).default_get(fields)
        res['partner_id'] = self.env.context.get('active_id')
        return res

    def commit_return(self):
        """
        确认按钮： 将修改客户的阶段状态并将原因写入到客户备注消息
        """
        self.ensure_one()
        self.partner_id.write({'c_stated': self.c_stated})
        note = "客户状态变更原因：{}".format(self.note)
        self.partner_id.message_post(body=note, message_type='notification')
        return {'type': 'ir.actions.act_window_close'}


class ResPartnerReturnChurn(models.TransientModel):
    _name = 'res.partner.crm.churn'
    _description = "客户流失"

    CHURMSTATE = [
        ('竞品赢单', '竞品赢单'),
        ('价格无法接受', '价格无法接受'),
        ('决策者不支持', '决策者不支持'),
        ('产品与业务不符', '产品与业务不符'),
        ('其他', '其他'),
    ]

    reason = fields.Selection(string="流失原因", selection=CHURMSTATE, default='其他')
    note = fields.Text(string="描述", required=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True)

    @api.model
    def default_get(self, fields):
        res = super(ResPartnerReturnChurn, self).default_get(fields)
        res['partner_id'] = self.env.context.get('active_id')
        return res

    def commit_churn(self):
        """
        将流失信息写入客户信息中
        """
        self.ensure_one()
        self.partner_id.write({'c_stated': 'churn'})
        note = "客户流失原因：{}".format(self.note)
        self.partner_id.message_post(body=note, message_type='notification')
        return {'type': 'ir.actions.act_window_close'}
