# -*- coding: utf-8 -*-
###################################################################################
# Copyright (C) 2019 SuXueFeng
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###################################################################################
{
    'name': "客户关系管理(CRM)",
    'summary': """客户管理、商机、线索等""",
    'description': """客户管理、商机、线索等""",
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'crm',
    'version': '12.0.1',
    'depends': ['base', 'mail', 'contacts'],
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

        'views/assets.xml',
        'views/crm_config.xml',
        'views/contact_users.xml',
        'views/res_partner.xml',
        'views/follow_records.xml',
        'views/sale_opportunity.xml',
        'views/sale_order.xml',
        'views/sale_contract.xml',

    ],
}
