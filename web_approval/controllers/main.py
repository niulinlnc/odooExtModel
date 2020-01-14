# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.main import MailController


class Mail(MailController):
    @http.route()
    def read_followers(self, follower_ids, res_model):
        followers = []
        is_editable = request.env.user.has_group('base.group_no_one')
        partner_id = request.env.user.partner_id
        follower_id = None
        follower_recs = request.env['mail.followers'].sudo().browse(follower_ids)
        # res_ids = follower_recs.mapped('res_id') # xichun
        # request.env[res_model].browse(res_ids).check_access_rule("read") # xichun
        for follower in follower_recs:
            is_uid = partner_id == follower.partner_id
            follower_id = follower.id if is_uid else follower_id
            followers.append({
                'id': follower.id,
                'name': follower.partner_id.name or follower.channel_id.name,
                'email': follower.partner_id.email if follower.partner_id else None,
                'res_model': 'res.partner' if follower.partner_id else 'mail.channel',
                'res_id': follower.partner_id.id or follower.channel_id.id,
                'is_editable': is_editable,
                'is_uid': is_uid,
            })
        return {
            'followers': followers,
            'subtypes': self.read_subscription_data(res_model, follower_id) if follower_id else None
        }


    @http.route()
    def mail_init_messaging(self):
        def get_static_mention_suggestions():
            suggestions = []
            employee_group = request.env.ref('base.group_user').sudo()
            hr_suggestions = [{'id': user.partner_id.id, 'name': user.name, 'email': user.email, 'cid': user.company_id.id} for user in employee_group.users]
            suggestions.append(hr_suggestions)

            return suggestions

        values = super(Mail, self).mail_init_messaging()
        values['mention_partner_suggestions'] = get_static_mention_suggestions()

        return values


















