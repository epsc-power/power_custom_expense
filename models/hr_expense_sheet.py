# -*- coding: utf-8 -*-
from odoo import models, api

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    @api.model
    def default_get(self, fields_list):
        # Get the standard default values first
        res = super(HrExpenseSheet, self).default_get(fields_list)

        # Override the employee_journal_id with the specific Miscellaneous Operations journal
        if 'employee_journal_id' in fields_list:
            misc_journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('name', '=', 'Miscellaneous Operations'),  # Targets the exact journal name
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if misc_journal:
                res['employee_journal_id'] = misc_journal.id
        return res