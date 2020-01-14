# -*- coding: utf-8 -*-
from . import models
from . import wizard
from . import controllers
from odoo.exceptions import UserError
from odoo import _

def uninstall_hook(cr, registry):
    raise UserError(_("该模块不允许卸载"))

