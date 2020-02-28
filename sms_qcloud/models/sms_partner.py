# -*- coding: utf-8 -*-

import logging
from odoo import models
from qcloudsms_py import SmsSingleSender
# --------取消证书验证-------
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
# -------------------------

_logger = logging.getLogger(__name__)


class SmsPartner(models.Model):
    _inherit = 'sms.partner'

    def send_message_code(self, user, phone, ttype):
        """
        发送验证码方法
        :param user: 系统用户
        :param phone: 手机号码
        :param ttype: 消息类型
        :return:
        """
        if self.code == 'qcloud':
            _logger.info(">>>{}-正在使用腾讯云短信发送验证码<<<".format(phone))
            templates = self.env['sms.template'].search([('partner_id', '=', self.id), ('ttype', '=', 'code')])
            if not templates:
                return {"state": False, 'msg': "发送失败：系统没有找到可用于发送验证码的模板"}
            s_sender = SmsSingleSender(self.app_id, self.app_key)
            random_number = self.generate_random_number()     # 获取验证码
            params = [random_number]
            message = ''
            for template in templates:
                try:
                    result = s_sender.send_with_param(86, phone, template.code, params, sign=template.signature_id.name)
                    logging.info(">>>qcloud-sms-result:{}".format(result))
                    if result['result'] == 0:
                        rec = self.create_verification_record(user, phone, result['sid'], random_number, template, ttype)
                        return {"state": True}
                    else:
                        message = result['errmsg']
                except Exception as e:
                    message = str(e)
            return {"state": False, 'msg': message}
        return super(SmsPartner, self).send_message_code(user, phone, ttype)

    def send_registration_message(self, user, phone):
        """
        新用户创建成功后发送通知短信：
        短信参数为两个参数，分别为账号和密码
        短信模板： 《您的账号已创建成功。账号：${username}，初始密码：${pwd}，请及时修改初始密码。》
        :param user:  创建的系统用户
        :param phone: 用户手机号码
        :return:
        """
        if self.code == 'qcloud':
            _logger.info(">>>{}-正在使用腾讯云短信发送新用户通知短信<<<".format(phone))
            s_sender = SmsSingleSender(self.app_id, self.app_key)
            params = [user.login, phone]
            templates = self.env['sms.template'].search([('partner_id', '=', self.id), ('ttype', '=', 'new_user')])
            if templates:
                for template in templates:
                    try:
                        result = s_sender.send_with_param(86, phone, template.code, params, sign=template.signature_id.name)
                        logging.info(">>>新用户通知结果:{}".format(result))
                        if result['result'] == 0:
                            rec = self.create_send_record(user, phone, template, 'new_user')
                            return True
                    except Exception as e:
                        _logger.info(">>>新用户通知异常:{}".format(str(e)))
        return super(SmsPartner, self).send_registration_message(user, phone)

