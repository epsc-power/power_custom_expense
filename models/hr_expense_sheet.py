# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    manager_approval_enabled = fields.Boolean(
        compute='_compute_manager_approval_enabled',
    )

    # NEW: Computed field to determine if the current user can see the button
    is_manager_approver = fields.Boolean(
        compute='_compute_is_manager_approver',
    )

    state = fields.Selection(
        selection_add=[
            ('approve', 'Employee Manager Approved'),
            ('manager_approved', 'Manager Approved'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('cancel', 'Refused'),
        ],
        ondelete={
            'manager_approved': 'set default',
        },
    )

    @api.depends_context('uid')
    def _compute_manager_approval_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'power_custom_expense.manager_approval'
        ) == 'True'
        for sheet in self:
            sheet.manager_approval_enabled = enabled

    # NEW: Compute method for button visibility
    @api.depends_context('uid')
    def _compute_is_manager_approver(self):
        manager_id_str = self.env['ir.config_parameter'].sudo().get_param(
            'power_custom_expense.manager_id'
        )
        manager_id = int(manager_id_str) if manager_id_str else False

        # Check if user is the designated manager OR an Expense Administrator
        is_designated = (self.env.user.id == manager_id)
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')

        for sheet in self:
            sheet.is_manager_approver = is_designated or is_admin

    @api.model
    def default_get(self, fields_list):
        res = super(HrExpenseSheet, self).default_get(fields_list)
        if 'employee_journal_id' in fields_list:
            misc_journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('name', '=', 'Miscellaneous Operations'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if misc_journal:
                res['employee_journal_id'] = misc_journal.id
        return res

    def _get_manager_id(self):
        manager_id = self.env['ir.config_parameter'].sudo().get_param(
            'power_custom_expense.manager_id'
        )
        return int(manager_id) if manager_id else False

    def action_approve_expense_sheets(self):
        custom_sheets = self.filtered(lambda s: s.manager_approval_enabled)
        standard_sheets = self - custom_sheets

        if standard_sheets:
            super(HrExpenseSheet, standard_sheets).action_approve_expense_sheets()

        if custom_sheets:
            custom_sheets.write({
                'state': 'approve',
                'user_id': self.env.user.id,
            })
        return True

    def action_manager_approve(self):
        if not self.manager_approval_enabled:
            raise UserError(_("Manager Approval is not enabled."))

        manager_id = self._get_manager_id()
        if not manager_id:
            raise UserError(_("Please configure the Approval Manager in Expense Settings."))

        # UPDATED: Allow Expense Administrators to bypass the strict manager_id check
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')
        if self.env.user.id != manager_id and not is_admin:
            raise AccessError(
                _("Only the configured Approval Manager or an Expense Administrator can approve this expense report."))

        for sheet in self:
            if sheet.state != 'approve':
                raise UserError(_("Only expense reports waiting for Manager Approval can be approved."))

            sheet.state = 'submit'
            super(HrExpenseSheet, sheet).action_approve_expense_sheets()

            sheet.state = 'manager_approved'

        self.activity_update()
        return True