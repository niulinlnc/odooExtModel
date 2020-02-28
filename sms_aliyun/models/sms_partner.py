# -*- coding: utf-8 -*-

import json
import logging
from odoo import models
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

_logger = logging.getLogger(__name__)


class SmsPartner(models.Model):
    _inherit = 'sms.partner'

    def send_message_code(self, user, phone, ttype):
        """
        重写发送验证码方法
        :param user: 系统用户
        :param phone: 手机号码
        :param ttype: 消息类型
        :return:
        """
        if self.code == 'aliyun':
            _logger.info(">>>{}-正在使用阿里云短信发送短信验证码<<<".format(phone))
            client = AcsClient(self.app_id, self.app_key, 'default')
            com_request = CommonRequest()
            com_request.set_accept_format('json')
            com_request.set_domain("dysmsapi.aliyuncs.com")
            com_request.set_method('POST')
            com_request.set_protocol_type('https')
            com_request.set_version('2017-05-25')
            com_request.set_action_name('SendSms')
            com_request.add_query_param('PhoneNumbers', phone)
            param_data = {
                'name': 'sms_sign',
                'code': self.generate_random_number()
            }
            param_json = json.dumps(param_data)
            com_request.add_query_param('TemplateParam', param_json)
            templates = self.env['sms.template'].search([('partner_id', '=', self.id), ('ttype', '=', 'code')])
            if not templates:
                return {"state": False, 'msg': "发送失败：系统没有找到可用于发送验证码的模板"}
            message = ''
            for template in templates:
                com_request.add_query_param('SignName', template.signature_id.name)
                com_request.add_query_param('TemplateCode', templates.code)
                try:
                    cli_response = client.do_action_with_exception(com_request)
                    cli_res = json.loads(str(cli_response, encoding='utf-8'))
                    logging.info("ali-sms-result: {}".format(cli_res))
                    if cli_res['Code'] == 'OK':
                        # 创建验证码记录
                        rec = self.create_verification_record(user, phone, cli_res['RequestId'], param_data['code'], template, ttype)
                        return {"state": True}
                    else:
                        message = cli_res['Message']
                except Exception as e:
                    return {"state": False, 'msg': "发送验证码失败,Error:{}".format(str(e))}
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
        if self.code == 'aliyun':
            _logger.info(">>>{}-正在使用阿里云短信发送新用户通知短信<<<".format(phone))
            client = AcsClient(self.app_id, self.app_key, 'default')
            com_request = CommonRequest()
            com_request.set_accept_format('json')
            com_request.set_domain("dysmsapi.aliyuncs.com")
            com_request.set_method('POST')
            com_request.set_protocol_type('https')
            com_request.set_version('2017-05-25')
            com_request.set_action_name('SendSms')
            com_request.add_query_param('PhoneNumbers', phone)
            param_data = {
                'username': user.login,
                'pwd': phone
            }
            param_json = json.dumps(param_data)
            com_request.add_query_param('TemplateParam', param_json)
            templates = self.env['sms.template'].search([('partner_id', '=', self.id), ('ttype', '=', 'new_user')])
            if templates:
                for template in templates:
                    com_request.add_query_param('SignName', template.signature_id.name)
                    com_request.add_query_param('TemplateCode', templates.code)
                    try:
                        cli_response = client.do_action_with_exception(com_request)
                        cli_res = json.loads(str(cli_response, encoding='utf-8'))
                        logging.info(">>>新用户通知结果: {}".format(cli_res))
                        if cli_res['Code'] == 'OK':
                            # 创建发送记录
                            rec = self.create_send_record(user, phone, template, 'new_user')
                            return True
                    except Exception as e:
                        _logger.info(">>>新用户通知异常:{}".format(str(e)))
        return super(SmsPartner, self).send_registration_message(user, phone)
