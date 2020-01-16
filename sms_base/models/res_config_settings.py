# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sms_auto_login = fields.Boolean(string=u'自动注册')
    sms_update_pwd = fields.Boolean(string=u'修改密码')
    sms_phone_login = fields.Boolean(string=u'手机号登陆')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            sms_auto_login=self.env['ir.config_parameter'].sudo().get_param('sms_base.sms_auto_login') or False,
            sms_update_pwd=self.env['ir.config_parameter'].sudo().get_param('sms_base.sms_update_pwd') or False,
            sms_phone_login=self.env['ir.config_parameter'].sudo().get_param('sms_base.sms_phone_login') or False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sms_base.sms_auto_login', self.sms_auto_login)
        self.env['ir.config_parameter'].sudo().set_param('sms_base.sms_update_pwd', self.sms_update_pwd)
        self.env['ir.config_parameter'].sudo().set_param('sms_base.sms_phone_login', self.sms_phone_login)
