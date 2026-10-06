from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manager_approval = fields.Boolean(
        string="Enable Manager Approval",
        config_parameter="power_custom_expense.manager_approval",
        help="Enable Manager Approval",
    )

    manager_id = fields.Many2one(
        'res.users',
        string="Approval Manager",
        config_parameter='power_custom_expense.manager_id',
    )