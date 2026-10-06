from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    manager_approval_enabled = fields.Boolean(
        compute='_compute_manager_approval_enabled',
    )

    approval_state = fields.Selection(
        selection_add=[
            ('manager_approved', 'Manager Approval'),
        ],
        ondelete={
            'manager_approved': 'set null',
        },
    )

    @api.depends_context('uid')
    def _compute_manager_approval_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'power_custom_expense.manager_approval'
        ) == 'True'

        for sheet in self:
            sheet.manager_approval_enabled = enabled

    def _get_manager_id(self):
        manager_id = self.env['ir.config_parameter'].sudo().get_param(
            'power_custom_expense.manager_id'
        )
        return int(manager_id) if manager_id else False

    def action_manager_approve(self):

        if not self.manager_approval_enabled:
            raise UserError(
                _("Manager Approval is not enabled.")
            )

        manager_id = self._get_manager_id()

        if not manager_id:
            raise UserError(
                _("Please configure the Approval Manager in Expense Settings.")
            )

        if self.env.user.id != manager_id:
            raise AccessError(
                _("Only the configured Approval Manager can approve this expense report.")
            )

        for sheet in self:

            if sheet.approval_state != 'approve':
                raise UserError(
                    _("Only expense reports waiting for Manager Approval can be approved.")
                )

            sheet.write({
                'approval_state': 'manager_approved',
            })

        self.activity_update()

        return True