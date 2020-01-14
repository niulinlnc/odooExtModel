# -*- coding: utf-8 -*-
from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(Http, self).session_info()
        res['is_approval_config'] = self.env.user.id in self.env.ref('web_approval.group_approval_config').users.ids
        return res

