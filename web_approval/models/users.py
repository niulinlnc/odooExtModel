# -*- coding: utf-8 -*-
from odoo import models, api, fields


class Users(models.Model):
    _inherit = 'res.users'

    job_name = fields.Char(u'岗位', compute='_compute_job_name')

    def _compute_job_name(self):
        employee_obj = self.env['hr.employee'].sudo()
        for user in self:
            employee = employee_obj.search([('user_id', '=', user.id)], limit=1)
            if employee and employee.job_id:
                user.job_name = employee.job_id.name

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # 一个节点有多个用户符合审批条件，需指定其中一个人来审批该节点，user_id_domain的值来限制该节点可以由哪些用户来审批
        context = self._context or {}
        if 'user_id_domain' in context:
            user_id_domain = [int(user_id) for user_id in context['user_id_domain'].split(',')]
            args = args or []
            args.append(('id', 'in', user_id_domain))

        return super(Users, self).name_search(name, args=args, operator=operator, limit=limit)


