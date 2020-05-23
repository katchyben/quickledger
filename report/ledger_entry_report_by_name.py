from odoo import api, models
from datetime import datetime
from odoo import exceptions
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ReportLedgerEntryByName(models.AbstractModel):
    _name = 'report.quickledger.report_ledger_entry_by_name'
    _description = 'Ledger Entry Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        fee_id = data['form']['payment_id']
        session_id = data['form']['session_id']
        faculty_id = data['form']['faculty_id']
        
        docs = self.env['academic.fee.entry'].search([('type_id', '=', fee_id),('session_id', '=', session_id)])
        _logger.info(f"Docs ::: {docs}")
        
        return {
            'doc_ids': self.ids,
            'doc_model': 'academic.fee.entry',
            'docs': docs
            }
