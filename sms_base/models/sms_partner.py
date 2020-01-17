# -*- coding: utf-8 -*-

import base64
import logging
import random
from odoo import fields, models, api
from odoo.modules import get_module_resource

_logger = logging.getLogger(__name__)


class SmsPartner(models.Model):
    _description = '短信服务商'
    _name = 'sms.partner'

    def _get_default_image(self):
        default_image_path = get_module_resource('sms_base', 'static/description', 'icon.png')
        return base64.b64encode(open(default_image_path, 'rb').read())

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='服务商名称', required=True, index=True)
    code = fields.Char(string='标识', required=True, index=True)
    image = fields.Binary(string="图标", default=_get_default_image)
    app_id = fields.Char(string='AccessKey', required=True)
    app_key = fields.Char(string='AccessSecret', help="Secret是用来校验短信发送请求合法性的密码", required=True)
    priority = fields.Integer(string=u'优先级(1-10)', default=5)
    code_length = fields.Integer(string=u'验证码长度', default=6)
    template_ids = fields.One2many(comodel_name='sms.template', inverse_name='partner_id', string=u'短信模板')

    def generate_random_number(self):
        """
        生成指定位数的随机数字字符串
        :param length_size:
        :return:
        """
        numbers = ""
        for i in range(self.code_length):
            ch = chr(random.randrange(ord('0'), ord('9') + 1))
            numbers += ch
        return numbers

    def send_message_code(self, user, phone):
        """
        发送短信验证码, 加载其他服务商时自行重写本方法来实现服务商的发送短信代码
        可参照 阿里云短信模块的发送代码
        :param user: 系统用户
        :param phone: 手机号码
        :return:
        """
        return {"state": False, 'msg': "无法通过错误的供应商发送验证码."}

    def send_registration_message(self, user, phone):
        """
        新用户创建成功后发送通知短信：
        短信参数为两个参数，分别为账号和密码
        可参照 阿里云短信模块的发送代码
        :param user:  创建的系统用户
        :param phone: 用户手机号码
        :return:
        """
        pass

    def create_verification_record(self, user, phone, sid, code, template):
        """
        创建发送手机号码验证码记录
        :param user: 系统用户
        :param phone: 手机号码
        :param sid: 返回的唯一标识
        :param code: 验证码
        :param template: 短信模板
        :return:
        """
        self.env['sms.verification.record'].sudo().create({
            'partner_id': template.partner_id.id,
            'template_id': template.id,
            'user_id': user.id,
            'phone': phone,
            'sid': sid,
            'code': code,
            'timeout': template.timeout,
        })
        return True

    def create_send_record(self, user, phone, template, ttype):
        """
        创建短信发送记录（不含验证码）
        :param user:  系统用户
        :param phone: 手机号码
        :param template: 短信模板
        :param ttype: 类型
        :return:
        """
        self.env['sms.send.record'].sudo().create({
            'partner_id': template.partner_id.id,
            'template_id': template.id,
            'signature_id': template.signature_id.id,
            'code': template.code,
            'user_id': user.id,
            'phone': phone,
            'ttype': ttype,
        })
        return True


