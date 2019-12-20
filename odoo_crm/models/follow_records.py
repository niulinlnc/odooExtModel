# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN License
###################################################################################

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CrmFollowRecords(models.Model):
    _description = '跟进记录'
    _name = 'crm.follow.records'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    FOLLOWTYPE = [
        ('00', '当面拜访'),
        ('01', '电话拜访'),
        ('02', '网络拜访'),
        ('03', '其他方式'),
    ]
    FOLLOWBUSINESS = [
        ('00', '销售机会'),
        ('01', '合同订单'),
        ('02', '报价单'),
        ('03', '其他'),
    ]

    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True, index=True)
    contact_id = fields.Many2one(comodel_name="crm.contact.users", string="联系人", domain="[('partner_id','=', partner_id)]")
    follow_type = fields.Selection(string="跟进方式", selection=FOLLOWTYPE, required=True)
    follow_time = fields.Datetime(string="拜访时间", required=True, default=fields.Datetime.now)
    follow_business = fields.Selection(string="跟进业务", selection=FOLLOWBUSINESS, default='03')
    note = fields.Text(string="备注", required=True)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='附件')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True)

    def attachment_image_preview(self):
        self.ensure_one()
        domain = [('res_model', '=', self._name), ('res_id', '=', self.id)]
        return {
            'domain': domain,
            'res_model': 'ir.attachment',
            'name': u'附件管理',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 20,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)


