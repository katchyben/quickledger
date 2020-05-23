from odoo import api, fields, models
from datetime import datetime
from odoo import exceptions
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class LedgerEntryWizard(models.TransientModel):
    _description = 'Ledger Entries Wizard'
    _name = 'ledger.entry.wizard'

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    @api.model
    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'NGN')], limit=1)

    session_id = fields.Many2one('academic.session', 'Session', required=True)
    faculty_id = fields.Many2one('quickledger.faculty', 'Faculty', required=True)
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    payment_id = fields.Many2one('payment.type', 'Payment', required=True)
    
    def print_report(self):
        data = {
            'ids': self.ids,
            'form': {
                'session_id': self.session_id.id,
                'payment_id': self.payment_id.id,
                'faculty_id': self.faculty_id.id
            }
        }
        return self.env.ref('quickledger.action_report_ledger_entry_by_name').report_action(self, data=data)

 
   