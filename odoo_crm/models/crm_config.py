# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CrmPartnerType(models.Model):
    _description = '客户类型'
    _name = 'crm.partner.type'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmPartnerNature(models.Model):
    _description = '客户性质'
    _name = 'crm.partner.nature'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmPartnerGrading(models.Model):
    _description = '客户分级'
    _name = 'crm.partner.grading'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmPartnerIndustry(models.Model):
    _description = '客户行业'
    _name = 'crm.partner.industry'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmPartnerSource(models.Model):
    _description = '客户来源'
    _name = 'crm.partner.source'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmPartnerStatedWork(models.Model):
    _name = 'crm.stated.work'
    _description = '阶段工作'
    _rec_name = 'c_stated'

    CUSTOMERSTATED = [
        ('find', '发现需求'),
        ('confirm', '确认需求'),
        ('solve', '解决方案'),
        ('talk', '商务谈判'),
        ('bid', '招投标'),
        ('clinch', '成交'),
        ('churn', '流失'),
    ]
    c_stated = fields.Selection(string="客户阶段", selection=CUSTOMERSTATED, required=True, index=True)
    content = fields.Char(string="工作内容", required=True, index=True)

    def name_get(self):
        return [(rec.id, "%s" % rec.content) for rec in self]


class CrmContractType(models.Model):
    _description = '合同类型'
    _name = 'crm.contract.type'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmContractPaymentMethod(models.Model):
    _description = '付款方式'
    _name = 'crm.contract.payment.method'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmContractLogisticsCompany(models.Model):
    _description = '物流公司'
    _name = 'crm.contract.logistics.company'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]


class CrmContractPaymentType(models.Model):
    _description = '回款类型'
    _name = 'crm.contract.payment.type'
    _rec_name = 'name'

    name = fields.Char(string="名称", required=True, index=True)
    code = fields.Char(string="简码")

    _sql_constraints = [('name_uniq', 'unique (name)', "名称已存在，请勿重复创建！")]
