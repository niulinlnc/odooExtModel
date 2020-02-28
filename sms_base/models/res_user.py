# -*- coding: utf-8 -*-
import datetime
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import AccessDenied
from odoo.http import request
import re

_logger = logging.getLogger(__name__)
phone_pat = re.compile("^(13\d|14[5|7]|15\d|166|17[3|6|7]|18\d)\d{8}$")


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    user_phone = fields.Char(string="手机号码", help="使用手机接受短信消息", index=True)

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
                if not re.search(phone_pat, res.user_phone):
                    raise UserError("抱歉：手机号码格式不正确，请重新输入！")

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
        # 判断是否开启手机号登录并且账号是否为手机
        if result and re.search(phone_pat, login):
            user = request.env['res.users'].sudo().search([('user_phone', '=', login)], limit=1)
            return super(ResUsers, cls).authenticate(db, user.login, password, user_agent_env)
        return super(ResUsers, cls).authenticate(db, login, password, user_agent_env)

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


class ChangePasswordWizard(models.TransientModel):
    _inherit = 'change.password.wizard'

    @api.multi
    def change_password_button(self):
        sms_update_pwd = self.env['ir.config_parameter'].sudo().get_param('sms_base.default_sms_update_pwd')
        # 判断是否启用需要验证码验证
        if sms_update_pwd:
            if len(self.user_ids) > 1:
                raise UserError("已启用手机验证码校验，不能批量修改密码！你可以关闭该功能后再进行批量操作！")
            result = self.env.ref('sms_base.change_password_user_sms_action').read()[0]
            user = phone = None
            for line in self.user_ids:
                if not line.new_passwd:
                    raise UserError("新的密码不能为空！")
                result['context'] = {
                    'default_phone': line.user_id.user_phone,
                    'default_password_user_id': line.id,
                    'default_user_id': line.user_id.id,
                    'default_new_passwd': line.new_passwd,
                }
                user = line.user_id
                phone = line.user_id.user_phone
            # 发送验证码
            partners = self.env['sms.partner'].sudo().get_partners_priority()
            if not partners:
                raise UserError("无可用的短信运营商，请联系管理员设置！")
            send_rec = partners.sudo().send_message_code(user, phone, 'passwd')
            if send_rec.get('state'):
                res = self.env.ref('sms_base.change_password_user_sms_form_view', False)
                result['views'] = [(res and res.id or False, 'form')]
                # 不要将临时密码在数据库中保留的时间超过必要的时间
                self.write({'new_passwd': False})
                return result
            else:
                raise UserError("发送验证码出错：{}".format(send_rec.get('msg')))
        else:
            return super(ChangePasswordWizard, self).change_password_button()


class ChangePasswordUserBySms(models.TransientModel):
    _name = 'change.password.user.sms'
    _description = '验证手机验证码'

    password_user_id = fields.Many2one(comodel_name="change.password.user", string="用户")
    phone = fields.Char(string="手机号码", readonly=True)
    code = fields.Char(string="验证码", required=True)
    user_id = fields.Many2one('res.users', string='用户', ondelete='cascade')
    new_passwd = fields.Char(string='密码')

    def change_password_button(self):
        """
        验证手机验证码，通过后修改密码
        :return:
        """
        self.ensure_one()
        # 检查验证码和登录手机是否匹配
        domain = [('phone', '=', self.phone), ('code', '=', self.code), ('state', '=', 'normal')]
        records = self.env['sms.verification.record'].sudo().search(domain)
        if not records:
            raise UserError("验证码不存在,请重新输入！")
        # 检查时效
        for record in records:
            if datetime.datetime.now() > record.end_time:
                record.sudo().write({'state': 'invalid'})
                raise UserError("验证码已失效！请重新发起!")
        records.sudo().write({'state': 'invalid'})
        self.write({'new_passwd': False})
        # 执行修改密码操作
        self.password_user_id.change_password_button()
        if self.env.user.id == self.password_user_id.user_id.id:
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {'type': 'ir.actions.act_window_close'}
