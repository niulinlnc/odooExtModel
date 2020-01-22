# -*- coding: utf-8 -*-

{
    'name': "腾讯云短信",
    'summary': """拓展sms使其可使用腾讯云短信的发信功能""",
    'description': """ 拓展sms使其可使用腾讯云短信的发信功能 """,
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'SMS',
    'version': '2.0',
    'depends': ['sms_base'],
    'installable': True,
    'application': False,
    'auto_install': True,

    'data': [
        'data/sms_partner_data.xml',
    ]
}