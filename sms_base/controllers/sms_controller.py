# -*- coding: utf-8 -*-
import datetime
import json
import logging
import werkzeug
from werkzeug.exceptions import BadRequest
from odoo import SUPERUSER_ID, api, http, _
from odoo import registry as registry_get
from odoo.addons.auth_oauth.controllers.main import OAuthController as Controller
from odoo.addons.web.controllers.main import (login_and_redirect, ensure_db)
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class OAuthController(Controller):

    @http.route('/web/login/sms', type='http', auth='public', website=True, sitemap=False)
    def web_odoo_sms_login(self, **kw):
        """
        短信登录入口,点击后返回到验证码界面
        :param kw:
        :return:
        """
        if request.session.uid:
            request.session.uid = False
        if request.session.login:
            request.session.login = False
        data = {'code_maxlength': 6}   # 验证码默认最大长度
        return request.render('sms_base.sms_login_signup', data)

    @http.route('/web/sms/send/code', type='http', auth="public", website=True, sitemap=False)
    def web_sms_send_code(self, **kw):
        """
        发送验证码
        :param kw:
        :return:
        """
        values = request.params.copy()
        user_phone = values.get('user_phone')
        if not user_phone:
            return json.dumps({'state': False, 'msg': "手机号码不能为空！"})
        _logger.info("手机号码:{}正在尝试发送验证码".format(user_phone))
        # 获取服务商
        partners = request.env['sms.partner'].sudo().get_partners_priority()
        if not partners:
            return json.dumps({"state": False, 'msg': "系统未找到可用的短信服务商，请联系管理员维护！"})
        # 验证员工是否有此手机号
        domain = [('user_phone', '=', user_phone)]
        user = request.env['res.users'].sudo().search(domain, limit=1)
        if not user:
            # 判断系统是否允许自动注册
            sms_auto_login = request.env['ir.config_parameter'].sudo().get_param('sms_base.default_sms_auto_login')
            if not sms_auto_login:
                return json.dumps({'state': False, 'msg': "抱歉，您的手机号未注册，请联系管理员完善信息！"})
            # 创建用户
            user = request.env['res.users'].sudo().create_user_by_sms_login(user_phone)
            # 发送通知短信
            partners.sudo().send_registration_message(user, user_phone)
        # 使用服务商的发送验证码函数
        result = partners.sudo().send_message_code(user, user_phone, 'login')
        if result.get('state'):
            return json.dumps({"state": True, 'msg': "验证码已发送，请注意查收短信！"})
        return json.dumps({"state": False, 'msg': result.get('msg')})

    @http.route('/web/sms/user/login', type='http', auth="public", website=True, sitemap=False)
    def web_sms_user_login(self, **kw):
        """
        验证登录验证码
        :param kw:
        :return:
        """
        values = request.params.copy()
        user_phone = values.get('phone')
        code = values.get('code')
        if not user_phone or not code:
            return json.dumps({'state': False, 'msg': "手机号和验证码不正确！"})
        # 检查验证码和登录手机有效性
        domain = [('phone', '=', user_phone), ('code', '=', code), ('state', '=', 'normal')]
        records = request.env['sms.verification.record'].sudo().search(domain)
        if not records:
            return json.dumps({'state': False, 'msg': "验证码不存在,请重新输入！"})
        # 检查时效
        for record in records:
            if datetime.datetime.now() > record.end_time:
                record.sudo().write({'state': 'invalid'})
                return json.dumps({'state': False, 'msg': "验证码已失效！请重新获取!"})
        records.sudo().write({'state': 'invalid'})
        # 验证通过执行登录操作
        return self.do_post_login(user_phone)

    def do_post_login(self, user_phone):
        """
        执行登录
        :param user_phone:
        :return:
        """
        if request.session.uid:
            request.session.uid = False
        if request.session.login:
            request.session.login = False
        ensure_db()
        dbname = request.session.db
        if not http.db_filter([dbname]):
            return BadRequest()
        registry = registry_get(dbname)
        with registry.cursor() as cr:
            try:
                env = api.Environment(cr, SUPERUSER_ID, {})
                credentials = env['res.users'].sudo().auth_oauth_sms('sms', user_phone)
                cr.commit()
                url = '/web'
                resp = login_and_redirect(*credentials, redirect_url=url)
                if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user.has_group('base.group_user'):
                    resp.location = '/'
                return json.dumps({'state': True, 'msg': "登录成功"})
            except AttributeError:
                return json.dumps({'state': False, 'msg': "未在数据库'%s'上安装auth_signup：oauth注册已取消" % (dbname)})
            except AccessDenied:
                _logger.info('>>>SMS-OAuth2: 访问被拒绝，在存在有效会话的情况下重定向到主页，而未设置Cookie')
                url = "/web/login?oauth_error=3"
                redirect = werkzeug.utils.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            except Exception as e:
                return json.dumps({'state': False, 'msg': "OAuth2: %s" % str(e)})
