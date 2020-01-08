# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrContract(models.Model):
    _inherit = "hr.contract"

    payroll_company = fields.Many2one(comodel_name='wage.archives.company', string=u'发薪公司', index=True)
    household_id = fields.Many2one(comodel_name='wage.household.registration', string=u'户籍性质', index=True)
    project_ids = fields.One2many(comodel_name='hr.contract.project', inverse_name='contract_id', string=u'薪资项目')
    amount_total = fields.Float(string=u'合计', digits=(10, 2), compute='_compute_amount_total')

    @api.onchange('employee_id')
    @api.constrains('employee_id')
    def _onchange_employee(self):
        """
        初始化所有薪资结构
        :return:
        """
        for res in self:
            if len(res.project_ids) < 1:
                structures = self.env['wage.structure'].search([])
                line_list = list()
                for structure in structures:
                    line_list.append({
                        'structure_id': structure.id,
                        'wage_amount': 0,
                    })
                res.project_ids = line_list

    @api.onchange('state')
    @api.constrains('state')
    def _constrains_state(self):
        for res in self:
            emp_count = self.search_count([('employee_id', '=', res.employee_id.id), ('state', '=', 'open')])
            if emp_count > 1:
                raise UserError("员工'%s'已有合同在运行中，只能存在一份合同在运行状态！！" % res.employee_id.name)

    def get_employee_wage_structure(self):
        """
        返回该员工的薪资结构数据
        :return:
        """
        amount_sum = 0
        structure_list = list()
        for line in self.project_ids:
            structure_list.append((0, 0, {
                'structure_id': line.structure_id.id,
                'wage_amount': line.wage_amount
            }))
            amount_sum += line.wage_amount
        return structure_list, amount_sum

    def _compute_amount_total(self):
        """
        计算合计
        """
        for res in self:
            amount_total = res.wage
            for line in res.project_ids:
                amount_total += line.wage_amount
            res.amount_total = amount_total


class HrContractProject(models.Model):
    _description = '薪资项目'
    _name = 'hr.contract.project'
    _rec_name = 'contract_id'

    sequence = fields.Integer(string=u'序号')
    contract_id = fields.Many2one(comodel_name='hr.contract', string=u'薪资合同')
    structure_id = fields.Many2one(comodel_name='wage.structure', string=u'薪资项目')
    wage_amount = fields.Float(string=u'薪资金额', digits=(10, 2))
