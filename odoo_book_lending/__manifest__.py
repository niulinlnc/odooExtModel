# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng GUN
###################################################################################
{
    'name': "图书借阅",
    'summary': """实现管理图书的借阅、归还功能""",
    'description': """实现管理图书的借阅、归还功能""",
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

        'data/default_num.xml',
        'data/config.xml',
        'views/assets.xml',
        'wizard/borrow_books.xml',
        'wizard/return_books.xml',

        'views/config.xml',
        'views/books.xml',
        'views/borrowing_records.xml',
        'views/books_pool_report.xml',
        'views/books_apply.xml',
        'views/books_purchase.xml',
    ],
}
