# -*- coding: utf-8 -*-

import datetime
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MealAlert(models.Model):
    _name = 'odoo.meal.alert'
    _description = '公告消息'
    _rec_name = 'message'

    ALERTSTATE = [
        ('specific', '指定日'),
        ('week', '每周'),
        ('days', '每天')
    ]

    display = fields.Boolean(compute='_compute_display_get')
    message = fields.Text('信息', required=True)
    alert_type = fields.Selection(ALERTSTATE, string='类型', required=True, index=True, default='specific')
    partner_id = fields.Many2one('res.partner', string="供应商")
    specific_day = fields.Date('日期', default=fields.Date.context_today)
    monday = fields.Boolean('星期一')
    tuesday = fields.Boolean('星期二')
    wednesday = fields.Boolean('星期三')
    thursday = fields.Boolean('星期四')
    friday = fields.Boolean('星期五')
    saturday = fields.Boolean('星期六')
    sunday = fields.Boolean('星期日')
    start_hour = fields.Float('介于', oldname='active_from', required=True, default=7)
    end_hour = fields.Float('和', oldname='active_to', required=True, default=23)
    active = fields.Boolean(default=True)

    @api.multi
    def name_get(self):
        return [(alert.id, '%s %s' % (_('公告'), '#%d' % alert.id)) for alert in self]

    @api.depends('alert_type', 'specific_day', 'monday', 'tuesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_hour', 'end_hour')
    def _compute_display_get(self):
        days_codes = {
            '0': 'sunday',
            '1': 'monday',
            '2': 'tuesday',
            '3': 'wednesday',
            '4': 'thursday',
            '5': 'friday',
            '6': 'saturday'
        }
        fullday = False
        now = datetime.datetime.now()
        if self.env.context.get('lunch_date'):
            lunch_date = fields.Datetime.from_string(self.env.context['lunch_date'])
            fullday = lunch_date > now
            now = max(lunch_date, now)
        mynow = fields.Datetime.context_timestamp(self, now)
        for alert in self:
            can_display_alert = {
                'specific': (str(alert.specific_day) == fields.Date.to_string(mynow)),
                'week': alert[days_codes[mynow.strftime('%w')]],
                'days': True
            }
            if can_display_alert[alert.alert_type]:
                hour_to = int(alert.end_hour)
                min_to = int((alert.end_hour - hour_to) * 60)
                to_alert = datetime.time(hour_to, min_to)
                hour_from = int(alert.start_hour)
                min_from = int((alert.start_hour - hour_from) * 60)
                from_alert = datetime.time(hour_from, min_from)

                if fullday or (from_alert <= mynow.time() <= to_alert):
                    alert.display = True
                else:
                    alert.display = False
