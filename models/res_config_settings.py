from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manager_approval = fields.Boolean(
        string="Enable Multiple Manager Approval",
        config_parameter="power_custom_expense.manager_approval",
        help="Enable Finance Manager Approval",
    )

    manager_id = fields.Many2one(
        'res.users',
        string="Approval Manager",
        config_parameter='power_custom_expense.manager_id',
    )

    sub_manager_id = fields.Many2one(
        'res.users',
        string="Fallback Sub-Manager (First Approver)",
        config_parameter='power_custom_expense.sub_manager_id',
        help="Gets the first approval if the employee has no manager set.",
    )