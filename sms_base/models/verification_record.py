# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
import datetime

_logger = logging.getLogger(__name__)


class SmsVerificationRecord(models.Model):
    _description = '验证码记录'
    _name = 'sms.verification.record'
    _rec_name = 'sid'
    _order = 'id'

    partner_id = fields.Many2one(comodel_name='sms.partner', string=u'服务商', ondelete='cascade', index=True)
    template_id = fields.Many2one(comodel_name='sms.template', string=u'模板', ondelete='cascade', index=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u'用户', index=True)
    phone = fields.Char(string='手机号码', index=True)
    sid = fields.Char(string='唯一标识')
    code = fields.Char(string='验证码')
    send_time = fields.Datetime(string=u'发送时间', default=fields.Datetime.now)
    end_time = fields.Datetime(string=u'截至时间')
    timeout = fields.Integer(string='有效时长(分钟)', default=30)
    state = fields.Selection(string=u'状态', selection=[('normal', '未验证'), ('invalid', '已验证'), ], default='normal')

    @api.model
    def create(self, values):
        values['end_time'] = datetime.datetime.now() + datetime.timedelta(minutes=values['timeout'])
        return super(SmsVerificationRecord, self).create(values)


class SmsSendRecord(models.Model):
    _name = 'sms.send.record'
    _description = '发送记录'
    _rec_name = 'create_date'
    _order = 'id'

    TEMPLATETYPE = [
        ('new_user', '新用户通知'),
        ('up_pwd', '修改密码通知'),
        ('notice', '消息通知'),
    ]

    create_date = fields.Datetime(string="创建时间", default=fields.Datetime.now, index=True)
    partner_id = fields.Many2one(comodel_name="sms.partner", string="服务商", index=True, ondelete='cascade')
    signature_id = fields.Many2one(comodel_name="sms.signature", string="短信签名", ondelete='cascade', index=True)
    template_id = fields.Many2one(comodel_name='sms.template', string=u'模板', ondelete='cascade', index=True)
    code = fields.Char(string="模板代码", index=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u'系统用户', index=True)
    phone = fields.Char(string="手机号码", index=True)
    ttype = fields.Selection(string="用于", selection=TEMPLATETYPE, default='code')
