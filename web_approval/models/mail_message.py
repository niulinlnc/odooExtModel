from odoo import api, models, modules, fields
from odoo.exceptions import UserError



class Message(models.Model):
    _inherit = 'mail.message'

    # instance_node_id = fields.Many2one('approval.flow.instance.node', u'实例节点', ondelete='cascade')
    # approval_swap = fields.Boolean(u'是审批沟通')
    parent_id = fields.Many2one('mail.message', 'Parent Message', index=True, ondelete='cascade', help="Initial thread message.")

    @api.multi
    def message_format(self):
        # xichun self.sudo()
        message_values = self.sudo().read([
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
            'channel_ids', 'partner_ids',  # recipients
            'starred_partner_ids',  # list of partner ids for whom the message is starred
            'moderation_status',
        ])
        message_tree = dict((m.id, m) for m in self.sudo())
        self._message_read_dict_postprocess(message_values, message_tree)

        # add subtype data (is_note flag, is_discussion flag , subtype_description). Do it as sudo
        # because portal / public may have to look for internal subtypes
        subtype_ids = [msg['subtype_id'][0] for msg in message_values if msg['subtype_id']]
        subtypes = self.env['mail.message.subtype'].sudo().browse(subtype_ids).read(['internal', 'description','id'])
        subtypes_dict = dict((subtype['id'], subtype) for subtype in subtypes)

        com_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')
        note_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

        # fetch notification status
        notif_dict = {}
        notifs = self.env['mail.notification'].sudo().search([('mail_message_id', 'in', list(mid for mid in message_tree)), ('is_read', '=', False)])
        for notif in notifs:
            mid = notif.mail_message_id.id
            if not notif_dict.get(mid):
                notif_dict[mid] = {'partner_id': list()}
            notif_dict[mid]['partner_id'].append(notif.res_partner_id.id)

        for message in message_values:
            message['needaction_partner_ids'] = notif_dict.get(message['id'], dict()).get('partner_id', [])
            message['is_note'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['id'] == note_id
            message['is_discussion'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['id'] == com_id
            message['is_notification'] = message['is_note'] and not message['model'] and not message['res_id']
            message['subtype_description'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['description']
            if message['model'] and self.env[message['model']]._original_module:
                message['module_icon'] = modules.module.get_module_icon(self.env[message['model']]._original_module)
        return message_values


    @api.multi
    def check_access_rule(self, operation):
        if 'approval_supper' in self._context:
            return

        return super(Message, self).check_access_rule(operation)


    @api.model
    def create(self, vals):
        # 沟通时，不去判断email_from，审批完成，不再创建沟通信息
        if 'model' in vals and 'res_id' in vals:
            if vals['model'] == 'mail.channel':
                channel_obj = self.env['mail.channel'].with_context(active_test=False).sudo()
                channel = channel_obj.browse(vals['res_id'])
                if not channel.active and channel.channel_type == 'swap':
                    raise UserError('审批完成，不能沟通！')

                vals['email_from'] = False

        return super(Message, self).create(vals)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _compute_domain(self):
        domain = [('model', '=', self._name)]
        try:
            subtype_id = self.env.ref('web_approval.mail_message_subtype_approval').id
            domain += [('subtype_id', '!=', subtype_id)]
        except:
            pass

        return domain

    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=_compute_domain, auto_join=True)


class Channel(models.Model):
    _inherit = 'mail.channel'

    channel_type = fields.Selection(selection_add=[('swap', u'沟通')])
    public = fields.Selection(selection_add=[('swap', u'沟通')])
    wait_approval_id = fields.Many2one('wait.approval', u'待审批', ondelete='cascade')
    active = fields.Boolean(u'活动', default=True)

    @api.model
    def channel_get_and_minimize(self, partners_to, **kwargs):
        channel = self.channel_get(partners_to, **kwargs)
        if channel:
            self.channel_minimize(channel['uuid'])
        return channel


    @api.model
    def channel_get(self, partners_to, pin=True, **kwargs):
        """ Get the canonical private channel between some partners, create it if needed.
            To reuse an old channel (conversation), this one must be private, and contains
            only the given partners.
            :param partners_to : list of res.partner ids to add to the conversation
            :param pin : True if getting the channel should pin it for the current user
            :returns a channel header, or False if the users_to was False
            :rtype : dict
        """
        if partners_to:
            channel_type = kwargs.get('chatType', 'chat')
            partners_to.append(self.env.user.partner_id.id)
            # determine type according to the number of partner in the channel
            self.env.cr.execute("""
                SELECT P.channel_id as channel_id
                FROM mail_channel C, mail_channel_partner P
                WHERE P.channel_id = C.id
                    AND C.public LIKE 'private'
                    AND P.partner_id IN %s
                    AND channel_type LIKE %s
                GROUP BY P.channel_id
                HAVING array_agg(P.partner_id ORDER BY P.partner_id) = %s
            """, (tuple(partners_to), channel_type, sorted(list(partners_to)),))
            result = self.env.cr.dictfetchall()
            if result:
                # get the existing channel between the given partners
                channel = self.browse(result[0].get('channel_id'))
                # pin up the channel for the current partner
                if pin:
                    self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write({'is_pinned': True})
            else:
                # create a new one
                name = u', '.join(self.env['res.partner'].sudo().browse(partners_to).mapped('name'))
                if kwargs.get('waitApprovalId'):
                    wait_approval = self.env['wait.approval'].browse(kwargs['waitApprovalId'])
                    model = self.env['ir.model'].sudo().search([('model', '=', wait_approval.model_name)])
                    name = u'审批%s沟通:%s' % (model.name, name, )

                channel = self.create({
                    'channel_partner_ids': [(4, partner_id) for partner_id in partners_to],
                    'public': 'private',
                    'channel_type': channel_type,
                    'email_send': False,
                    'name': name,
                    'wait_approval_id': kwargs.get('waitApprovalId', False)
                })
                # broadcast the channel header to the other partner (not me)
                channel._broadcast(partners_to)
            return channel.channel_info()[0]
        return False


    @api.model
    def channel_fetch_slot(self):
        res = super(Channel, self).channel_fetch_slot()
        my_partner_id = self.env.user.partner_id.id
        pinned_channels = self.env['mail.channel.partner'].search([('partner_id', '=', my_partner_id)]).mapped('channel_id')
        swap_channels = self.search([('channel_type', '=', 'swap'), ('id', 'in', pinned_channels.ids)])
        res['channel_swap'] = swap_channels.channel_info()

        return res

    @api.multi
    def channel_info(self, extra_info = False):
        channel_infos = []
        partner_channels = self.env['mail.channel.partner']
        # find the channel partner state, if logged user
        if self.env.user and self.env.user.partner_id:
            partner_channels = self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', 'in', self.ids)])
        # for each channel, build the information header and include the logged partner information
        for channel in self:
            info = {
                'id': channel.id,
                'name': channel.name,
                'uuid': channel.uuid,
                'state': 'open',
                'is_minimized': False,
                'channel_type': channel.channel_type,
                'public': channel.public,
                'mass_mailing': channel.email_send,
                'moderation': channel.moderation,
                'is_moderator': self.env.uid in channel.moderator_ids.ids,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
            }
            if extra_info:
                info['info'] = extra_info
            # add the partner for 'direct mesage' channel
            if channel.channel_type in ['chat', 'swap']:
                info['direct_partner'] = (channel.sudo()
                                          .with_context(active_test=False)
                                          .channel_partner_ids
                                          .filtered(lambda p: p.id != self.env.user.partner_id.id)
                                          .read(['id', 'name', 'im_status']))

            # add last message preview (only used in mobile)
            if self._context.get('isMobile', False):
                last_message = channel.channel_fetch_preview()
                if last_message:
                    info['last_message'] = last_message[0].get('last_message')

            # add user session state, if available and if user is logged
            if partner_channels.ids:
                partner_channel = partner_channels.filtered(lambda c: channel.id == c.channel_id.id)
                if len(partner_channel) >= 1:
                    partner_channel = partner_channel[0]
                    info['state'] = partner_channel.fold_state or 'open'
                    info['is_minimized'] = partner_channel.is_minimized
                    info['seen_message_id'] = partner_channel.seen_message_id.id
                # add needaction and unread counter, since the user is logged
                info['message_needaction_counter'] = channel.message_needaction_counter
                info['message_unread_counter'] = channel.message_unread_counter
            channel_infos.append(info)
        return channel_infos







