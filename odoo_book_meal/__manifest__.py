# -*- coding: utf-8 -*-

{
    'name': "员工订餐",
    'summary': """员工预定早、中晚餐、菜单、价格""",
    'description': """实现员工预定早、中晚餐、菜单、价格""",
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'book',
    'version': '12.0.1',
    'depends': ['base', 'mail'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'data/config.xml',
        'data/default_num.xml',

        'views/assets.xml',
        'views/meal_type.xml',
        'views/meal_product.xml',
        'views/meal_alert.xml',
        'views/meal_order.xml',
    ],
}
