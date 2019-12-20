# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CUSTOMERSTATED = [
    ('find', '发现需求'),
    ('confirm', '确认需求'),
    ('solve', '解决方案'),
    ('talk', '商务谈判'),
    ('bid', '招投标'),
    ('clinch', '成交'),
    ('churn', '流失'),
]


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = '客户管理'

    CUSTOMERSTATE = [
        ('potential', '潜在客户'),
        ('init', '初步接触'),
        ('last', '持续跟进'),
        ('clinch', '成交客户'),
        ('loyalty', '忠诚客户'),
        ('invalid', '无效客户'),
    ]
    CUSTOMERTIMPORTTANCE = [
        ('bottom', '低'),
        ('during', '中'),
        ('high', '高'),
        ('major', '非常重要')
    ]

    c_abbreviation = fields.Char(string="客户简称")
    c_state = fields.Selection(string="客户状态", selection=CUSTOMERSTATE, default='potential', index=True)
    c_stated = fields.Selection(string="客户阶段", selection=CUSTOMERSTATED, default='find', index=True)
    c_principal_ids = fields.Many2many("res.users", "c_partner_and_principal_rel", string="负责人")
    c_collaborator_ids = fields.Many2many("res.users", "c_partner_and_collaborator_rel", string="协同人")
    c_type_id = fields.Many2one(comodel_name="crm.partner.type", string="客户类型")
    c_nature_id = fields.Many2one(comodel_name="crm.partner.nature", string="客户性质")
    c_grading_id = fields.Many2one(comodel_name="crm.partner.grading", string="客户分级")
    c_industry_id = fields.Many2one(comodel_name="crm.partner.industry", string="客户行业")
    c_importance = fields.Selection(string="重要程度", selection=CUSTOMERTIMPORTTANCE)
    c_source_id = fields.Many2one(comodel_name="crm.partner.source", string="客户来源")
    c_website = fields.Char(string="客户官网")
    c_introduction = fields.Text(string="客户简介")
    customer = fields.Boolean(string="客户", default=True)
    c_parent_id = fields.Many2one(comodel_name="res.partner", string="上级客户")
    c_recommended_id = fields.Many2one(comodel_name="res.partner", string="推荐人")
    c_contact_ids = fields.One2many(comodel_name="crm.contact.users", inverse_name="partner_id", string="联系人")
    c_follow_record_ids = fields.One2many(comodel_name="crm.follow.records", inverse_name="partner_id", string="跟进记录")
    c_stated_word_ids = fields.One2many(comodel_name="res.partner.stated.word", inverse_name="partner_id", string="阶段工作")

    def create_follow_records(self):
        """
        新建客户跟进记录
        """
        action = self.env.ref('odoo_crm.crm_follow_records_action')
        result = action.read()[0]
        result['context'] = {
            'default_partner_id': self.id,
        }
        result['target'] = 'new'
        res = self.env.ref('odoo_crm.crm_follow_records_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result

    @api.constrains('c_stated')
    @api.onchange('c_stated')
    def _onchange_stated(self):
        """
        获取阶段对应的工作
        """
        if len(self.c_stated_word_ids) == 0:
            stateds = self.env['crm.stated.work'].search([])
            stated_list = list()
            for stated in stateds:
                stated_list.append({
                    'c_stated': stated.c_stated,
                    'stated_id': stated.id,
                    'is_complete': False,
                })
            self.c_stated_word_ids = stated_list

    def next_stated(self):
        """
        下一阶段
        """
        # 检查当前阶段内的工作是否全部完成
        for res in self:
            for word in res.c_stated_word_ids:
                if word.c_stated == res.c_stated:
                    if not word.is_complete:
                        raise UserError("当前阶段内还有未完成的工作：({})。".format(word.stated_id.content))
            # 进入下一阶段
            if res.c_stated == 'find':
                res.c_stated = 'confirm'
            elif res.c_stated == 'confirm':
                res.c_stated = 'solve'
            elif res.c_stated == 'solve':
                res.c_stated = 'talk'
            elif res.c_stated == 'talk':
                res.c_stated = 'bid'
            elif res.c_stated == 'bid':
                res.c_stated = 'clinch'

    def action_partner_opportunity(self):
        """
        跳转至该客户的机会列表
        """
        result = self.env.ref('odoo_crm.crm_sale_opportunity_action').read()[0]
        result['context'] = {'default_partner_id': self.id}
        result['domain'] = "[('partner_id','=',%s)]" % (self.id)
        return result

    def action_sale_order(self):
        """
        跳转报价单
        """
        result = self.env.ref('odoo_crm.crm_sale_order_action').read()[0]
        result['context'] = {'default_partner_id': self.id}
        result['domain'] = "[('partner_id','=',%s)]" % (self.id)
        return result

    def action_sale_contract(self):
        """
        跳转至订单合同
        """
        result = self.env.ref('odoo_crm.crm_sale_contract_action').read()[0]
        result['context'] = {'default_partner_id': self.id}
        result['domain'] = "[('partner_id','=',%s)]" % (self.id)
        return result


class CrmPartnerStatedWord(models.Model):
    _name = 'res.partner.stated.word'
    _description = '阶段工作内容'

    c_stated = fields.Selection(string="所属阶段", selection=CUSTOMERSTATED, index=True)
    stated_id = fields.Many2one(comodel_name="crm.stated.work", string="阶段工作", required=True)
    is_complete = fields.Boolean(string="已完成", default=False, index=True)
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", index=True)

    @api.constrains('is_complete')
    def _constrains_complete(self):
        """
        当完成状态发生变化时，将信息写入到客户的消息备注中
        """
        self.ensure_one()
        # 获取阶段字符串
        stated_str = ''
        for cu in CUSTOMERSTATED:
            if self.c_stated == cu[0]:
                stated_str = cu[1]
                break
        stated = "完成" if self.is_complete else "关闭"
        note = "{}-阶段任务：{}， 新状态：{}".format(stated_str, self.stated_id.content, stated)
        self.partner_id.message_post(body=note, message_type='notification')