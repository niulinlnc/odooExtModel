# -*- coding: utf-8 -*-
{
    'name': '工作流审批引擎',
    'category': 'approval',
    'author': 'www.sxfblog.com',
    'version': '1.0',
    'summary': '工作流审批引擎、配置单据审批流程',
    'website': 'https://www.sxfblog.com/',
    'license': 'OEEL-1',
    'description': '',
    'depends': ['web', 'mail', 'hr'],
    'external_dependencies': {'python': ['networkx']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/menu.xml',
        'views/ir_model_approve.xml',
        'views/approval_flow_view.xml',
        'views/wait_approval_summary_view.xml',
        'views/record_approval_state_summary_view.xml',
        'views/approval_copy_for_summary_view.xml',
        'views/record_approval_state_view.xml',

        'views/assets.xml',

        'wizard/approval_wizard_view.xml',
        'wizard/dispatch_approval_user_wizard_veiw.xml',
        'wizard/approval_turn_to_wizard_view.xml',
        'wizard/add_node_action_wizard_view.xml',
        'wizard/approval_increase_wizard_view.xml',

        'data/approval_node.xml',
        'data/mail_message_subtype.xml',
        'data/mail_channel.xml',
        'data/increase_type.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': False,
    'application': True,

    'uninstall_hook': 'uninstall_hook',
}


