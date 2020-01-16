# -*- coding: utf-8 -*-

{
    'name': "阿里云短信",
    'summary': """使用阿里云短信发送短信消息""",
    'description': """ 使用阿里云短信发送短信消息 """,
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'SMS',
    'version': '2.0',
    'depends': ['sms_base'],
    'installable': True,
    'application': True,
    'auto_install': True,

    'data': [
        'data/sms_partner_data.xml',
    ]
}