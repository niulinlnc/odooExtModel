# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class InsuredSchemeInsurance(models.Model):
    _name = 'insured.scheme.insurance'
    _description = "社保种类"
    _rec_name = 'name'
    _order = 'id'

    active = fields.Boolean(string=u'Active', default=True)
    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='险种名称', required=True)
    base_number = fields.Float(string=u'险种基数', digits=(10, 2))
    company_number = fields.Float(string=u'公司比例', digits=(10, 2))
    company_fixed_number = fields.Float(string=u'公司固定金额', digits=(10, 2))
    personal_number = fields.Float(string=u'个人比例', digits=(10, 2))
    personal_fixed_number = fields.Float(string=u'个人固定金额', digits=(10, 2))


class ProvidentFundKind(models.Model):
    _name = 'provident.fund.kind'
    _description = "公积金种类"
    _rec_name = 'name'
    _order = 'id'

    active = fields.Boolean(string=u'Active', default=True)
    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='名称', required=True)
    base_number = fields.Float(string=u'基数', digits=(10, 2))
    company_number = fields.Float(string=u'公司比例', digits=(10, 2))
    company_fixed_number = fields.Float(string=u'公司固定金额', digits=(10, 2))
    personal_number = fields.Float(string=u'个人比例', digits=(10, 2))
    personal_fixed_number = fields.Float(string=u'个人固定金额', digits=(10, 2))


class InsuredScheme(models.Model):
    _description = '参保方案'
    _name = 'insured.scheme'
    _rec_name = 'name'
    _order = 'id'

    @api.model
    def _get_default_country_id(self):
        return self.env['res.company']._company_default_get('payment.transaction').country_id.id

    active = fields.Boolean(string=u'Active', default=True)
    name = fields.Char(string='方案名称', required=True)
    country_id = fields.Many2one(comodel_name='res.country', string=u'国家', default=_get_default_country_id)
    country_state_id = fields.Many2one(comodel_name='res.country.state', string=u'参保城市', index=True,
                                       domain="[('country_id', '=?', country_id)]")
    line_ids = fields.One2many('insured.scheme.line', inverse_name='scheme_id', string=u'社保种类')
    provident_ids = fields.One2many('insured.scheme.provident.line', inverse_name='scheme_id', string=u'公积金种类')
    notes = fields.Text(string=u'备注')

    def create_all_insurance(self):
        """
        把所有的险种信息拉取到列表中
        :return:
        """
        for res in self:
            insurances = self.env['insured.scheme.insurance'].search([])
            line_list = list()
            for insurance in insurances:
                line_list.append({
                    'insurance_id': insurance.id,
                    'base_number': insurance.base_number,
                    'ttype': 'base',
                    'company_number': insurance.company_number,
                    'personal_number': insurance.personal_number,
                })
            res.line_ids = line_list

    @api.onchange('name')
    @api.constrains('name')
    def _pull_all_insurance(self):
        for res in self:
            if len(res.line_ids) < 1:
                self.create_all_insurance()


class InsuredSchemeLine(models.Model):
    _description = '社保种类列表'
    _name = 'insured.scheme.line'
    _rec_name = 'scheme_id'
    _order = 'id'

    sequence = fields.Integer(string=u'序号')
    scheme_id = fields.Many2one(comodel_name='insured.scheme', string=u'参保方案')
    insurance_id = fields.Many2one(comodel_name='insured.scheme.insurance', string=u'险种', required=True)
    ttype = fields.Selection(string=u'计算方式', selection=[('base', '按比例'), ('fixed', '按固定值'), ], default='base', required=True)
    base_number = fields.Float(string=u'险种基数', digits=(10, 2))
    company_number = fields.Float(string=u'公司比例', digits=(10, 2))
    company_fixed_number = fields.Float(string=u'公司固定金额', digits=(10, 2))
    personal_number = fields.Float(string=u'个人比例', digits=(10, 2))
    personal_fixed_number = fields.Float(string=u'个人固定金额', digits=(10, 2))

    @api.onchange('insurance_id')
    def _onchange_insurance_id(self):
        """
        动态获取险种参数
        :return:
        """
        for res in self:
            if res.insurance_id:
                res.base_number = res.insurance_id.base_number
                res.company_number = res.insurance_id.company_number
                res.company_fixed_number = res.insurance_id.company_fixed_number
                res.personal_number = res.insurance_id.personal_number
                res.personal_fixed_number = res.insurance_id.personal_fixed_number
                res.ttype = 'base'


class InsuredSchemeProvidentLine(models.Model):
    _description = '公积金种类列表'
    _name = 'insured.scheme.provident.line'
    _rec_name = 'scheme_id'
    _order = 'id'

    sequence = fields.Integer(string=u'序号')
    scheme_id = fields.Many2one(comodel_name='insured.scheme', string=u'参保方案')
    insurance_id = fields.Many2one(comodel_name='provident.fund.kind', string=u'公积金种类', required=True)
    ttype = fields.Selection(string=u'计算方式', selection=[('base', '按比例'), ('fixed', '按固定值'), ], default='base', required=True)
    base_number = fields.Float(string=u'公积金基数', digits=(10, 2))
    company_number = fields.Float(string=u'公司比例', digits=(10, 2))
    company_fixed_number = fields.Float(string=u'公司固定金额', digits=(10, 2))
    personal_number = fields.Float(string=u'个人比例', digits=(10, 2))
    personal_fixed_number = fields.Float(string=u'个人固定金额', digits=(10, 2))

    @api.onchange('insurance_id')
    def _onchange_insurance_id(self):
        """
        动态获取险种参数
        :return:
        """
        for res in self:
            if res.insurance_id:
                res.base_number = res.insurance_id.base_number
                res.company_number = res.insurance_id.company_number
                res.company_fixed_number = res.insurance_id.company_fixed_number
                res.personal_number = res.insurance_id.personal_number
                res.personal_fixed_number = res.insurance_id.personal_fixed_number