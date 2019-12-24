# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################
{
    'name': "客户关系管理(CRM)",
    'summary': """客户管理、机会、报价、合同、发票等""",
    'description': """客户管理、机会、报价、合同、发票等""",
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'crm',
    'version': '12.0.1',
    'depends': ['base', 'mail', 'product'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/crm_config.xml',
        'data/default_num.xml',

        'wizard/res_partner.xml',
        'wizard/sale_opportunity.xml',

        'views/assets.xml',
        'views/crm_config.xml',
        'views/contact_users.xml',
        'views/res_partner.xml',
        'views/follow_records.xml',
        'views/sale_opportunity.xml',
        'views/sale_order.xml',
        'views/sale_contract.xml',
        'views/sale_order_returns.xml',
        'views/sale_invoice.xml',
        'views/work_order.xml',
    ],
}
