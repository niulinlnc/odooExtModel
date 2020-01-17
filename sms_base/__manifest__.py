# -*- coding: utf-8 -*-

{
    'name': "SMS短信应用",
    'summary': """使odoo支持手机一键登录、修改用户密码、找回密码""",
    'description': """ SMS短信应用 """,
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'SMS',
    'version': '2.0',
    'depends': ['base', 'auth_oauth'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'data': [
        'data/auth_oauth_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/res_users.xml',
        'views/sms_partner.xml',
        'views/sms_signature.xml',
        'views/sms_template.xml',
        'views/verification_record.xml',
        'views/web_templates.xml',
        'views/new_user_groups.xml',
    ]
}