# -*- coding: utf-8 -*-
from lxml import etree

from odoo import fields, models, api


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('approval_diagram', '审批流程图')])



fields_view_get_origin = models.BaseModel.fields_view_get

@api.model
def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    result = fields_view_get_origin(self, view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    view_get_approval_flow(self, view_type, result)
    return result


models.BaseModel.fields_view_get = fields_view_get


def modify_tree_view(obj, result):
    fields_info = obj.fields_get(allfields=['doc_approval_state'])
    if 'doc_approval_state' in fields_info:
        field = fields_info['doc_approval_state']
        field.update({'view': {}})
        result['fields']['doc_approval_state'] = field

        root = etree.fromstring(result['arch'])
        field = etree.Element('field')
        field.set('name', 'doc_approval_state')
        field.set('widget', 'approval_state')
        root.append(field)

        result['arch'] = etree.tostring(root)


def modify_form_view(self, result, flows):
    # 是否存在<header>
    root = etree.fromstring(result['arch'])
    headers = root.xpath('header')
    if not headers:
        header = etree.Element('header')
        root.insert(0, header)
    else:
        header = headers[0]
    for flow in flows:
        if flow.approval_cannot_run:
            for method in flow.approval_cannot_run.split(','):
                if root.xpath("//header/button[@name='" + method + "']"):
                    for item in root.xpath("//header/button[@name='" + method + "']"):
                        item.set('context', "{'approval_callback': 0}")

    # 提交审批
    button = etree.Element('button')
    button.set('string', u'提交审批')
    # model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
    # approval_flow = self.env['approval.flow'].search([('model_id', '=', model_id)])
    # if approval_flow:
    #     state = approval_flow.model_state_filed_value_id.state_value
    #     if self.state != state:
    #         button.set('modifiers', '{"invisible": []}')
    button.set('class', 'btn-primary commit_approval o_hidden')
    button.set('type', 'object')
    button.set('name', 'commit_approval')
    header.insert(len(header.xpath('button')), button)

    # 暂停审批
    button = etree.Element('button')
    button.set('class', 'pause_approval o_hidden')
    button.set('string', u'暂停审批')
    button.set('type', 'object')
    button.set('name', 'pause_approval')
    header.insert(len(header.xpath('button')), button)

    # 恢复审批
    button = etree.Element('button')
    button.set('string', u'恢复审批')
    button.set('class', 'btn-primary resume_approval o_hidden')
    button.set('type', 'object')
    button.set('name', 'resume_approval')
    header.insert(len(header.xpath('button')), button)

    # 取消审批
    button = etree.Element('button')
    button.set('class', 'cancel_approval o_hidden')
    button.set('string', u'取消审批')
    button.set('type', 'object')
    button.set('name', 'cancel_approval')
    button.set('confirm', '确认取消审批吗？')
    header.insert(len(header.xpath('button')), button)

    # # 审批
    # button = etree.Element('button')
    # button.set('string', u'审批')
    # button.set('class', 'btn-primary approval o_hidden')
    # button.set('type', 'action')
    # button.set('name', str(self.env.ref('web_approval.approval_wizard_action').id))
    # header.insert(len(header.xpath('button')), button)

    # # 沟通
    # button = etree.Element('button')
    # button.set('string', u'沟通')
    # button.set('class', 'btn-do-swap o_hidden')
    # button.set('type', 'object')
    # button.set('name', 'cancel_approval')
    # header.insert(len(header.xpath('button')), button)


    # mail.chatter
    chatter = root.xpath('//div[@class="oe_chatter"]')
    if not chatter:
        form = root.xpath('//form')[0]
        chatter = etree.SubElement(form, 'div')
        chatter.set('class', 'oe_chatter')

    result['arch'] = etree.tostring(root)


def view_get_approval_flow(self, view_type, result):
    if view_type not in ['form', 'tree']:
        return

    flow_obj = self.env.get('approval.flow')
    if flow_obj is None:
        return

    model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
    flows = flow_obj.with_context(active_test=False).search([('model_id', '=', model_id)])
    if not flows:
        return

    if view_type == 'tree':
        modify_tree_view(self, result)

    if view_type == 'form':
        modify_form_view(self, result, flows)


# load_views_origin = models.BaseModel.load_views
#
#
# @api.model
# def load_views(self, views, options=None):
#     result = load_views_origin(self, views, options=None)
#     params = self.env.context.get('params', False)
#     if not params:
#         res_id = False
#     else:
#         res_id = params.get('id')
#     for view_type, fields_view in result['fields_views'].items():
#         root = etree.fromstring(fields_view['arch'])
#         model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)]).id
#         approval_state = self.env['record.approval.state'].search(
#             [('model', '=', self._name), ('res_id', '=', res_id)])
#         if approval_state.approval_state != 'complete':
#             model_button_blacklist = self.env['ps.model.button.value'].search([
#                 ('model_id', '=', model_id), ('is_blacklist', '=', True), ('is_submit_approval', '=', True)])
#             for model_button in model_button_blacklist:
#                 for item in root.xpath("//header/button[@name='" + model_button.button_name + "']"):
#                     item.set('modifiers', '{"invisible": []}')
#         fields_view['arch'] = etree.tostring(root)
#     return result


# models.BaseModel.load_views = load_views

