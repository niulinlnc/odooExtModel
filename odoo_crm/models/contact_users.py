# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN License
###################################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmContactUsers(models.Model):
    _description = '联系人'
    _name = 'crm.contact.users'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_company(self):
        return self.env.user.company_id

    DECISIONRELATION = [
        ('00', '关键决策人'),
        ('01', '分项决策人'),
        ('02', '商务决策人'),
        ('03', '技术决策人'),
        ('04', '财务决策人'),
        ('05', '使用者'),
        ('06', '意见影响者'),
        ('07', '普通人'),
    ]

    active = fields.Boolean(string="有效", default=True)
    color = fields.Integer(string="Color")
    name = fields.Char(string="名称", required=True, index=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="关联客户", index=True)
    mobile = fields.Char(string="手机号码", required=True, index=True)
    email = fields.Char(string="Email")
    qq = fields.Char(string="QQ")
    weixin = fields.Char(string="微信")
    address = fields.Char(string="地址")
    sex = fields.Selection(string="性别", selection=[('male', '男'), ('female', '女')], default='male')
    birthday = fields.Date(string="生日")
    hobby = fields.Char(string="爱好")
    department = fields.Char(string="部门")
    post = fields.Char(string="职务")
    level = fields.Selection(string="级别", selection=[('high', '高层'), ('middle', '中层'), ('basic', '基层')], default='middle')
    decision_relationship = fields.Selection(string="决策关系", selection=DECISIONRELATION, default='02')
    note = fields.Text(string="备注")
    company_id = fields.Many2one('res.company', '公司', default=_get_default_company, index=True, required=True)

    def action_contact_opportunity(self):
        """
        跳转至该联系人的机会列表
        """
        result = self.env.ref('odoo_crm.crm_sale_opportunity_action').read()[0]
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_contact_ids': [(6, 0, [self.id])]}
        result['domain'] = "[('contact_ids','=', %s)]" % (self.id)
        return result

    def create_contact_opportunity(self):
        """
        新建联系人机会
        """
        result = self.env.ref('odoo_crm.crm_sale_opportunity_action').read()[0]
        result['context'] = {
            'default_name': "%s的销售机会" % (self.name),
            'default_partner_id': self.partner_id.id,
            'default_contact_ids': [(6, 0, [self.id])]
        }
        res = self.env.ref('odoo_crm.crm_sale_opportunity_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result

    def create_sale_contract(self):
        """
        新建合同
        """
        result = self.env.ref('odoo_crm.crm_sale_contract_action').read()[0]
        result['context'] = {
            'default_name': "%s的销售合同" % (self.name),
            'default_partner_id': self.partner_id.id,
            'default_contact_ids': [(6, 0, [self.id])]
        }
        res = self.env.ref('odoo_crm.crm_sale_contract_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result

    def action_sale_contract(self):
        """
        跳转至合同
        """
        result = self.env.ref('odoo_crm.crm_sale_contract_action').read()[0]
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_contact_ids': [(6, 0, [self.id])]}
        result['domain'] = "[('contact_ids','=', %s)]" % (self.id)
        return result

