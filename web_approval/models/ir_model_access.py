# -*- coding: utf-8 -*-
from odoo import models, api, tools


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    @tools.ormcache_context('self._uid', 'model', 'mode', 'raise_exception', keys=('lang',))
    def check(self, model, mode='read', raise_exception=True):
        if 'approval_supper' in self._context:
            return True

        return super(IrModelAccess, self).check(model, mode=mode, raise_exception=raise_exception)


class Users(models.Model):
    _inherit = 'res.users'

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        context = self._context or {}
        # 配置审批流程时，用超级管理员得到所有用户
        if 'approval_supper' in context:
            self = self.sudo()

        return super(Users, self).read(fields, load=load)


class Job(models.Model):
    _inherit = 'hr.job'

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        context = self._context or {}
        # 配置审批流程时，用超级管理员得到所有用户
        if 'approval_supper' in context:
            self = self.sudo()

        return super(Job, self).read(fields, load=load)


Model = models.Model
origin_apply_ir_rules = Model._apply_ir_rules

@api.model
def _apply_ir_rules(self, query, mode='read'):
    if 'approval_supper' in self._context:
        return

    return origin_apply_ir_rules(self, query, mode)

Model._apply_ir_rules = _apply_ir_rules


origin_check_access_rule = Model.check_access_rule


@api.multi
def check_access_rule(self, operation):
    context = self._context or {}
    if 'approval_supper' in context:
        return

    return origin_check_access_rule(self, operation)

Model.check_access_rule = check_access_rule

