# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manager_approval = fields.Boolean(
        string="Enable Multiple Manager Approval",
        config_parameter="power_custom_expense.manager_approval",
        help="Enable Multiple Manager Approval",
    )

    sub_manager_id = fields.Many2one(
        'res.users',
        string="Manager (First Approver)",
        config_parameter='power_custom_expense.sub_manager_id',
        help="Gets the first approval if the employee has no manager set.",
    )

    manager_id = fields.Many2one(
        'res.users',
        string="Finance Manager",
        config_parameter='power_custom_expense.manager_id',
    )