# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.exceptions import AccessDenied
from odoo.http import request
import re

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    user_phone = fields.Char(string="手机号码", help="用于用户使用手机接受短信消息", index=True)

    @api.constrains('user_phone')
    def constrains_user_phone(self):
        """
        检查手机号码是否符合规则
        :return:
        """
        for res in self:
            if res.user_phone:
                users_count = self.env['res.users'].sudo().search_count([('user_phone', '=', res.user_phone)])
                if users_count > 1:
                    raise UserError("抱歉！{}手机号码已被占用,请解除或更换号码!".format(res.user_phone))

    @api.model
    def auth_oauth_sms(self, provider, params):
        if provider == 'sms':
            users = self.search([('user_phone', '=', params)])
        else:
            users = self.search([('oauth_provider_id', '=', provider), ('oauth_uid', '=', params)])
        if not users or len(users) > 1:
            raise AccessDenied()
        return (self.env.cr.dbname, users[0].login, params)

    @api.model
    def _check_credentials(self, password):
        try:
            return super(ResUsers, self)._check_credentials(password)
        except AccessDenied:
            res = self.sudo().search([('id', '=', self.env.uid), ('user_phone', '=', password)])
            if not res:
                raise

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """
        检查是否允许使用手机号码登录
        :param db:
        :param login:
        :param password:
        :param user_agent_env:
        :return:
        """
        result = request.env['ir.config_parameter'].sudo().get_param('sms_base.default_sms_phone_login')
        phone_pat = re.compile("^(13\d|14[5|7]|15\d|166|17[3|6|7]|18\d)\d{8}$")
        # 判断是否开启手机号登录并且账号是否为手机
        if result and re.search(phone_pat, login):
            user = request.env['res.users'].sudo().search([('user_phone', '=', login)], limit=1)
            return super(ResUsers, cls).authenticate(db, user.login, password, user_agent_env)
        return super(ResUsers, cls).authenticate(db, login, password, user_agent_env)

    # def send_change_password_sms(self, login, password, phone):
    #     """
    #     发送修改密码通知短信
    #     :param login:
    #     :param password:
    #     :param phone:
    #     :return:
    #     """
    #     services = self.env['sms.service.config'].sudo().search([('state', '=', 'open')])
    #     if not services:
    #         return {'state': False, 'msg': "短信服务平台已关闭,请联系管理员处理"}
    #     result = False
    #     for service in services:
    #         if service.sms_type == 'tencent':
    #             result = self._send_change_pwd_sms_by_tencent(login, password, service, phone)
    #             logging.info(result)
    #             if result['state']:
    #                 break
    #         elif service.sms_type == 'ali':
    #             logging.info("正在使用阿里云短信平台")
    #             result = self._send_change_pwd_sms_by_aliyun(login, password, service, phone)
    #             logging.info(result)
    #             if result['state']:
    #                 break
    #     if result['state']:
    #         return {"state": True, 'msg': "通知短信已发送"}
    #     else:
    #         return {"state": False, 'msg': result['msg']}
    #
    # def _send_change_pwd_sms_by_tencent(self, login, password, service, phone):
    #     """
    #     腾讯云发送修改密码通知短信
    #     腾讯云短信通知模板: "你好: 你的账户信息已发生改变，新的账户信息为：用户名：{1}，密码：{2}，请及时登录系统并进行修改！"
    #     :param login:
    #     :param password:
    #     :param service:
    #     :param phone:
    #     :return:
    #     """
    #     template_id, sms_sign, timeout = self._get_sms_config_template(service, 'change_pwd')
    #     if not template_id or not sms_sign or not timeout:
    #         return {"state": False, 'msg': "在(短信服务配置)中没有找到可用于(修改密码通知模板)的模板,请联系管理员设置！"}
    #     s_sender = SmsSingleSender(service.app_id, service.app_key)
    #     params = [login, password]
    #     try:
    #         result = s_sender.send_with_param(86, phone, template_id, params, sign=sms_sign, extend="", ext="")
    #         logging.info("tencent-sms-change-pwd:{}".format(result))
    #         if result['result'] == 0:
    #             return {"state": True}
    #         else:
    #             return {"state": False, 'msg': "腾讯云发送修改密码短信失败!,Error:{}".format(result['errmsg'])}
    #     except Exception as e:
    #         return {"state": False, 'msg': "腾讯云发送修改密码短信失败,Error:{}".format(str(e))}
    #
    # def _send_change_pwd_sms_by_aliyun(self, login, password, service, phone):
    #     """
    #     通过阿里云发送修改密码通知短信
    #     短信模板为： "你好: 你的账户信息已发生改变，新的账户信息为：用户名：${name}，密码：${pwd}，请及时登录系统查看或进行修改！"
    #     :param login:
    #     :param password:
    #     :param service:
    #     :param phone:
    #     :return:
    #     """
    #     client = AcsClient(service.app_id, service.app_key, 'default')
    #     com_request = CommonRequest()
    #     com_request.set_accept_format('json')
    #     com_request.set_domain("dysmsapi.aliyuncs.com")
    #     com_request.set_method('POST')
    #     com_request.set_protocol_type('https')
    #     com_request.set_version('2017-05-25')
    #     com_request.set_action_name('SendSms')
    #     template_id, sms_sign, timeout = self._get_sms_config_template(service, 'change_pwd')
    #     if not template_id or not sms_sign or not timeout:
    #         return {"state": False, 'msg': "在(短信服务配置)中没有找到可用于(登录时发送验证码)的模板,请联系管理员设置！"}
    #     com_request.add_query_param('PhoneNumbers', phone)
    #     com_request.add_query_param('SignName', sms_sign)
    #     com_request.add_query_param('TemplateCode', template_id)
    #     param_data = {
    #         'name': login,
    #         'pwd': password
    #     }
    #     param_json = json.dumps(param_data)
    #     com_request.add_query_param('TemplateParam', param_json)
    #     try:
    #         cli_response = client.do_action_with_exception(com_request)
    #         cli_res = json.loads(str(cli_response, encoding='utf-8'))
    #         logging.info("ali-sms-result: {}".format(cli_res))
    #         if cli_res['Code'] == 'OK':
    #             return {"state": True}
    #         else:
    #             return {"state": False, 'msg': "阿里云发送修改密码短信失败!,Error:{}".format(cli_res['Message'])}
    #     except Exception as e:
    #         return {"state": False, 'msg': "阿里云发送修改密码短信失败,Error:{}".format(str(e))}

    @api.model
    def create_user_by_sms_login(self, phone):
        """
        通过手机号创建系统用户
        """
        if not phone:
            return False
        # 创建Odoo用户
        values = {
            'active': True,
            "login": phone,
            "user_phone": phone,
            "password": phone,
            "name": phone,
            'email': phone,
        }
        # 初始新用户权限
        sms_group_id = self.env['ir.config_parameter'].sudo().get_param('sms_base.default_sms_group_id')
        groups = self.env['new.user.groups'].sudo().search([('id', '=', sms_group_id)], limit=1)
        if not groups:
            values['groups_id'] = self.env.ref('base.group_user')
        else:
            values['groups_id'] = [(6, 0, groups.groups_ids.ids)]
        user = self.sudo().create(values)
        return user