# -*- coding: utf-8 -*-
###################################################################################
#    Copyright (C) 2019 SuXueFeng  GNU
###################################################################################
{
    'name': "社保管理",
    'summary': """管理员工的社保，每月生成月结账单等""",
    'description': """管理员工的社保，每月生成月结账单等""",
    'author': "Su-XueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'dingtalk',
    'version': '12.0',
    'depends': ['base', 'mail', 'hr'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/default_date.xml',
        'views/assets.xml',
        'views/insured_scheme.xml',
        'views/insured_scheme_emp.xml',
        'views/insured_monthly_statement.xml',
        'views/employee_month_report.xml',
        'wizard/insured_monthly_statement.xml'
    ],
    'qweb': [
        'static/xml/*.xml'
    ]
}
