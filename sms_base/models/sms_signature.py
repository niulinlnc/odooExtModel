# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class SmsSignature(models.Model):
    _description = '签名管理'
    _name = 'sms.signature'

    SMSSOURCE = [
        ('0', '企事业单位的全称或简称'),
        ('1', '工信部备案网站的全称或简称'),
        ('2', 'APP应用的全称或简称'),
        ('3', '公众号或小程序的全称或简称'),
        ('4', '电商平台店铺名的全称或简称'),
        ('5', '商标名的全称或简称'),
    ]

    name = fields.Char(string="签名名称", required=True, help="无须添加【】、()、[]符号，签名发送会自带【】符号，避免重复", index=True)
    partner_id = fields.Many2one(comodel_name="sms.partner", string="服务商", index=True, ondelete='cascade')
    ttype = fields.Selection(string="适用场景", selection=[('code', '验证码'), ('message', '通知/通用')], required=True, default='code')
    source = fields.Selection(string="来源", selection=SMSSOURCE, default='1')
    remark = fields.Text(string="签名说明")
    state = fields.Selection(string="状态", selection=[('00', '待应用'), ('01', '已应用')], default='00', index=True)

    def confirm_apply(self):
        """
        应用签名
        :return:
        """
        self.write({'state': '01'})

    def return_draft(self):
        """
        取消应用
        :return:
        """
        self.write({'state': '00'})