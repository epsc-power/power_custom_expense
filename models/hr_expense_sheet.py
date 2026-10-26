# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    manager_approval_enabled = fields.Boolean(
        compute='_compute_manager_approval_enabled',
    )
    is_manager_approver = fields.Boolean(
        compute='_compute_is_manager_approver',
    )
    is_sub_manager_approver = fields.Boolean(
        compute='_compute_is_sub_manager_approver',
    )

    state = fields.Selection(
        selection_add=[
            ('approve', 'Employee Manager Approved'),
            ('sub_manager_approved', 'Manager Approved'),
            ('manager_approved', 'Finance Manager Approved'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('cancel', 'Refused'),
        ],
        ondelete={
            'sub_manager_approved': 'set default',
            'manager_approved': 'set default',
        },
    )

    def action_submit_sheet(self):
        for sheet in self:
            if sheet.manager_approval_enabled:
                sub_manager_id_str = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.sub_manager_id')
                sub_manager_id = int(sub_manager_id_str) if sub_manager_id_str else False

                if sub_manager_id and not sheet.user_id:
                    sheet.user_id = sub_manager_id

        return super(HrExpenseSheet, self).action_submit_sheet()

    @api.depends_context('uid')
    def _compute_manager_approval_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.manager_approval') == 'True'
        for sheet in self:
            sheet.manager_approval_enabled = enabled

    @api.depends_context('uid')
    def _compute_is_manager_approver(self):
        manager_id_str = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.manager_id')
        manager_id = int(manager_id_str) if manager_id_str else False
        is_designated = (self.env.user.id == manager_id)
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')
        for sheet in self:
            sheet.is_manager_approver = is_designated or is_admin

    @api.depends_context('uid')
    def _compute_is_sub_manager_approver(self):
        sub_manager_id_str = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.sub_manager_id')
        sub_manager_id = int(sub_manager_id_str) if sub_manager_id_str else False
        is_designated = (self.env.user.id == sub_manager_id)
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')
        for sheet in self:
            sheet.is_sub_manager_approver = is_designated or is_admin

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
        manager_id = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.manager_id')
        return int(manager_id) if manager_id else False

    def _get_sub_manager_id(self):
        sub_manager_id = self.env['ir.config_parameter'].sudo().get_param('power_custom_expense.sub_manager_id')
        return int(sub_manager_id) if sub_manager_id else False

    # TIER 1: Employee Manager Approval
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
            # Send Activity to First Approver (Sub Manager)
            sub_manager_id = self._get_sub_manager_id()
            if sub_manager_id:
                for sheet in custom_sheets:
                    sheet.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_("Manager Approval Required"),
                        note=_("Awaiting Manager (First Approver) sign-off."),
                        user_id=sub_manager_id
                    )
        return True

    # TIER 2: First Approver (Sub Manager)
    def action_sub_manager_approve(self):
        if not self.manager_approval_enabled:
            raise UserError(_("Manager Approval is not enabled."))

        sub_manager_id = self._get_sub_manager_id()
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')

        if not sub_manager_id and not is_admin:
            raise UserError(_("Please configure the Manager (First Approver) in Settings."))

        if self.env.user.id != sub_manager_id and not is_admin:
            raise AccessError(_("Only the Manager (First Approver) or an Admin can approve this stage."))

        for sheet in self:
            if sheet.state != 'approve':
                raise UserError(_("Only expense reports waiting for First Approver can be approved."))

            sheet.state = 'sub_manager_approved'

            # Send Activity to Final Finance Manager
            manager_id = self._get_manager_id()
            if manager_id:
                sheet.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Finance Manager Approval Required"),
                    note=_("Awaiting final Finance Manager sign-off."),
                    user_id=manager_id
                )

        self.activity_update()
        return True

    # TIER 3: Final Finance Manager
    def action_manager_approve(self):
        if not self.manager_approval_enabled:
            raise UserError(_("Manager Approval is not enabled."))

        manager_id = self._get_manager_id()
        is_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager')

        if not manager_id and not is_admin:
            raise UserError(_("Please configure the Finance Manager in Expense Settings."))

        if self.env.user.id != manager_id and not is_admin:
            raise AccessError(_("Only the configured Finance Manager or an Expense Administrator can approve this expense report."))

        for sheet in self:
            if sheet.state != 'sub_manager_approved':
                raise UserError(_("Only expense reports waiting for Finance Manager Approval can be approved."))

            # SAFETEY CHECK: Only create Journal Entry if it doesn't already exist (fixes issues for old records)
            if not sheet.account_move_ids:
                sheet.state = 'submit'
                super(HrExpenseSheet, sheet).action_approve_expense_sheets()

            sheet.state = 'manager_approved'

        self.activity_update()
        return True