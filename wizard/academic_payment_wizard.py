from odoo import api, fields, models
from datetime import datetime
from odoo import exceptions
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AcademicPaymentWizard(models.TransientModel):
    _description = 'Academic Payment Wizard'
    _name = 'academic.payment.wizard'

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    @api.model
    def _default_fee_type(self):
        bbf = self.env.ref('quickledger.bbf_fee')
        _logger.info(f"BBF ::: {bbf}")
        return self.env['payment.type'].search([('name', '=ilike', 'Balance Brought Forword')], limit=1)

    @api.model
    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'NGN')], limit=1)

    session_id = fields.Many2one('academic.session', 'Session', required=True)
    programme_id = fields.Many2one('quickledger.programme', string='Programme', required=True)
    diploma_id = fields.Many2one(related='programme_id.diploma_id', string="Degree",  readonly=True)
    payment_date = fields.Date('Payment Date', required=True)
    bank_id = fields.Many2one('res.partner.bank', 'Bank')
    level_id = fields.Many2one('quickledger.level', 'Level', required=True)
    amount = fields.Monetary('Amount Paid', currency_field='currency_id')
    teller_number = fields.Char('Teller #')
    receipt_number = fields.Char('Receipt #')
    payment_type = fields.Selection(
        string='Payment Type',
        selection=[('Balance Brought Forward', 'Balance Brought Forward'), 
                   ('Others', 'Other Payments')],
        default='Others'
    )
    transaction_type = fields.Selection(
        string='Transaction Type',
        selection=[('Cash', 'Cash Payment'), ('Bank', 'Bank Payment')],
        default='Bank'
    )
    student_id = fields.Many2one('quickledger.student', 'Student', required=True)
    outstanding_fee_ids = fields.Many2many('academic.fee.entry', string='Outstanding Fees')
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    balance = fields.Monetary(compute="_compute_balance", currency_field='currency_id',  string="Previous Balance", readonly=True)
    fee_id = fields.Many2one('academic.fee.entry', 'Hostel Payment Entry', required=False)
    payment_id = fields.Many2one('payment.type', 'Payment', required=False, default=_default_fee_type)
    amount_due = fields.Monetary(compute="_compute_amount_due", string='Amount Due', currency_field='currency_id', readonly=True)

    @api.depends('payment_type')
    def _compute_amount_due(self):
        for record in self:
            if record.payment_type == 'Balance Brought Forward':
                bbf = record.student_id.balance_brought_forward
                record.amount_due = bbf
            else:
                record.amount_due = 0.00


    @api.constrains('amount')
    def _check_amount_greater_than_zero(self):
        for payment in self:
            if payment.payment_type == 'Balance Brought Forward':
                if payment.amount_due <= 0:
                    raise ValidationError('Payment Amount must be greater than 0')
                elif payment.amount <= 0:
                    raise ValidationError('Payment Amount must be greater than 0')
                elif payment.amount > payment.amount_due:
                    raise ValidationError('Payment Amount must be greater than Amount Due')
                else:
                    return True
            else:
                return True


    @api.depends('student_id')
    def _compute_balance(self):
        for record in self:
            record.balance = record.student_id.ledger_id.total_balance

    @api.constrains('amount')
    def _check_amount_not_greater_than_fees(self):
        for payment in self:
            if payment.payment_type == 'Balance Brought Forward':
                if payment.amount > payment.amount_due:
                    raise ValidationError('Amount Paid cannot be greater than Hostel Fee')
            else:
                fees_total = sum([fee.balance for fee in payment.outstanding_fee_ids])
                if payment.amount > fees_total and payment.amount > payment.balance:
                    raise ValidationError('Amount Paid cannot be greater than Fees total or Balance')

    @api.constrains('payment_date')
    def _check_date(self):
        for payment in self:
            payment_date = datetime.strptime(str(payment.payment_date), '%Y-%m-%d')
            date_today = datetime.strptime(str(fields.Date.context_today(payment)), '%Y-%m-%d')
            if (payment_date > date_today):
                raise ValidationError('Payment Date cannot be in the future')

    @api.constrains('teller_number')
    def _check_bank(self):
        for payment in self:
            if payment.bank_id:
                if not payment.teller_number:
                    raise ValidationError('Please provide Teller Number')
    
    def do_process_payment(self):
        self.ensure_one()
        AcademicPaymentEntry = self.env['academic.payment.entry']
        StudentLedgerEntry = self.env['student.ledger.entry']
        AcademicFeeEntry = self.env['academic.fee.entry']
        AcademicFee = self.env['academic.fee']
        StudentLedger = self.env['student.ledger']
        StudentRegistration = self.env['student.registration']
        AcademicFee = self.env['academic.fee']
        PaymentType = self.env['payment.type']

        student_id = self.student_id.id
        level_id = self.level_id.id
        diploma_id = self.diploma_id.id
        session_id = self.session_id.id
        ledger = StudentLedger.search([('student_id', '=', student_id)])

        vals = {}
        vals['session_id'] = session_id
        vals['programme_id'] = self.programme_id.id
        vals['student_id'] = student_id
        vals['level_id'] = level_id
        vals['ledger_id'] = ledger.id
        vals['bank_id'] = self.bank_id.id
        vals['teller_number'] = self.teller_number
        vals['amount'] = self.amount
        vals['payment_date'] = self.payment_date
        registration = StudentRegistration.search([('student_id', '=', student_id),('session_id', '=', session_id)])
        processed_fees = []
        payment_amount = self.amount

        # Payment of Balance Brought Forward' Fee Workflow
        if self.payment_type == 'Balance Brought Forward':
            payment_id = self.payment_id.id
            new_balance = self.student_id.balance_brought_forward - self.amount
            self.student_id.write({'balance_brought_forward' : new_balance})
            return AcademicPaymentEntry.create(vals)
        else:
            for fee in self.outstanding_fee_ids.filtered(lambda f: f.balance > 0.00).sorted(key=lambda f: f.balance, reverse=True):
                if fee.balance >= payment_amount and payment_amount > 0.00:
                    fee.write({'amount_paid' : (fee.amount_paid + payment_amount)})
                    payment_amount = 0.00
                    processed_fees.append(fee.id)
                    break
                elif fee.balance < payment_amount and payment_amount > 0.00:
                    payment_amount = payment_amount - fee.balance
                    fee.write({'amount_paid' : fee.amount_due})
                    processed_fees.append(fee.id)
                else:
                    pass

            vals['fee_ids'] = [(6, 0, processed_fees)]
            return AcademicPaymentEntry.create(vals)

    @api.depends('student_id', 'session_id')
    def _compute_fees(self):
        StudentLedger = self.env['student.ledger']
        domain = [('student_id', '=', self.student_id.id)]
        ledger = StudentLedger.search(domain)
        self.outstanding_fee_ids = ledger.fee_entry_ids.\
        filtered(lambda f: (f.session_id.id == self.session_id.id) and f.amount_due > f.amount_paid)
