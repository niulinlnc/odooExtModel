# -*- coding: utf-8 -*-
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
CUSTOMERTIMPORTTANCE = [
    ('bottom', '低'),
    ('during', '中'),
    ('high', '高'),
    ('major', '非常重要')
]


class SaleOpportunity(models.Model):
    _name = 'crm.sale.opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '销售机会'
    _rec_name = 'code'
    _order = 'id'

    active = fields.Boolean(string="归档", default=True, track_visibility='onchange')
    color = fields.Integer(string="Color")
    code = fields.Char(string="机会编号", required=True, default='New', track_visibility='onchange')
    name = fields.Char(string="机会名称", required=True, track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name="res.partner", string="客户", required=True, index=True, track_visibility='onchange')
    contact_ids = fields.Many2many("crm.contact.users", "crm_opportunity_and_contract_rel", "opportunity_id", 'contract_id',
                                   string="联系人", domain="[('partner_id','=', partner_id)]")
    state = fields.Selection(string="销售阶段", selection=SALESTATED, default='find', track_visibility='onchange')
    principal_ids = fields.Many2many("res.users", "opportunity_principal_and_res_users_rel", "opportunity_id", 'user_id',string="负责人", required=True)
    collaborator_ids = fields.Many2many("res.users", "opportunity_collaborator_and_res_users_rel", "opportunity_id", 'user_id', string="协同人")
    importance = fields.Selection(string="重要程度", selection=CUSTOMERTIMPORTTANCE, default='during')
    decision_makers = fields.Many2many("crm.contact.users", "opportunity_decision_and_users_rel", "opportunity_id", 'user_id', string="决策人",
                                       domain="[('partner_id','=', partner_id)]")
    competitors = fields.Char(string="竞争对手")
    product_ids = fields.Many2many("product.template", "crm_opportunity_and_product_rel", 'opportunity_id', 'product_id', string="关联产品")
    estimated_amount = fields.Float(string="预计金额",  required=True, track_visibility='onchange')
    estimated_date = fields.Date(string="结束日期", required=True, default=fields.Date.context_today, track_visibility='onchange')
    note = fields.Text(string="备注")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='附件')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.user.company_id, index=True)

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('crm.sale.opportunity.code')
        return super(SaleOpportunity, self).create(values)
    
    def attachment_image_preview(self):
        self.ensure_one()
        domain = [('res_model', '=', self._name), ('res_id', '=', self.id)]
        return {
            'domain': domain,
            'res_model': 'ir.attachment',
            'name': u'附件',
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

    def action_sale_order(self):
        """
        跳转至报价单
        """
        result = self.env.ref('odoo_crm.crm_sale_order_action').read()[0]
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_contact_ids': [(6, 0, self.contact_ids.ids)]}
        result['domain'] = "[('partner_id', '=', %s)]" % (self.partner_id.id)
        return result

    def create_sale_order(self):
        """
        新建报价单
        """
        result = self.env.ref('odoo_crm.crm_sale_order_action').read()[0]
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_opportunity_ids': [(6,0,[self.id])]}
        res = self.env.ref('odoo_crm.crm_sale_order_form_view', False)
        result['views'] = [(res and res.id or False, 'form')]
        return result
