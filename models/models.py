# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api, tools, exceptions
from odoo.modules.module import get_module_resource
import logging
import re

_logger = logging.getLogger(__name__)


class Semester(models.Model):
    """ Defining an academic year """
    _name = "quickledger.semester"
    _description = "Semester"
    _order = "sequence asc"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Name', size=64, required=True, index=1, help='Name')
    code = fields.Char('Code', required=True, index=1, help='Code')
    
    
class EntryStatus(models.Model):
    """ Defining an academic year """
    _name = "quickledger.entry.status"
    _description = "Entry Status"
    _order = "name asc"

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', required=True)


class Department(models.Model):
    _name = "quickledger.department"
    _description = "Department"
    _order = 'name'

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=64, required=True)
    previous_code = fields.Char('Previous Code', size=64, required=False)
    faculty_id = fields.Many2one('quickledger.faculty', 'Faculty', required=True)
    diploma_ids = fields.Many2many(comodel_name='quickledger.diploma', string='Degrees')
    student_ids = fields.One2many('quickledger.student', 'department_id', 'Student', readonly=True)
    programme_ids = fields.One2many('quickledger.programme', 'department_id', 'Programmes', readonly=True)
    position_entry_ids = fields.One2many('quickledger.position.entry', 'department_id', 'Entries', readonly=True)
    classification_id = fields.Many2one(string="Classification", related="faculty_id.classification_id", readonly=True)


class Programme(models.Model):
    _name = "quickledger.programme"
    _description = "Academic Programme"
    _order = 'department_id asc'
    
    @api.model
    def _get_default_status(self):
        return self.env['quickledger.entry.status'].search([('name', '=', 'UME')], limit=1)

    name = fields.Char(compute='_compute_name', string="Name", store=True)
    department_id = fields.Many2one('quickledger.department', 'Department', required=True)
    faculty_id = fields.Many2one('quickledger.faculty', 'Faculty', required=True)
    diploma_id = fields.Many2one('quickledger.diploma', 'Degree', required=True)
    course_ids = fields.One2many('programme.course.entry', 'programme_id', 'Courses')
    school_id = fields.Many2one(related='faculty_id.school_id', readonly=True, store=True)
    entry_status_id = fields.Many2one('quickledger.entry.status', 'Entry Status', default=_get_default_status)
    applicable_fee_ids = fields.Many2many('academic.fee', compute='_get_fees', string='Applicable Fees', store=True, readonly=True)
    duration = fields.Integer(string='Programme Duration', default="4")
    classification_id = fields.Many2one(string="Classification", related="faculty_id.classification_id", readonly=True)

    def _get_applicable_fees_by_level(self, level_id):
        for programme in self:
            return programme.faculty_id.fee_ids.filtered(lambda f: f.level_id.id == level_id)
        return []

    @api.depends('faculty_id.fee_ids')
    def _get_fees(self):
        for record in self:
            diploma_type = record.diploma_id.type_id
            faculty = record.faculty_id
            record.applicable_fee_ids = faculty._get_applicable_fees_by_diploma(diploma_type.id)

    @api.depends('department_id', 'diploma_id')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.diploma_id.code} {record.department_id.name}"

    @api.depends('department_id', 'diploma_id')
    def _compute_name(self):
        for record in self:
            if record.entry_status_id and record.entry_status_id.code == "CEP":
                record.name = f"{record.diploma_id.code} {record.department_id.name} { record.entry_status_id.code}"
            else:
                record.name = f"{record.diploma_id.code} {record.department_id.name}"


class FacultyClassification(models.Model):
    _name = "quickledger.faculty.classification"
    _description = "Faculty Classification"
    _order = "name"

    code = fields.Char("Code", required=False)
    name = fields.Char("Name", required=True)
    fee_ids = fields.One2many('academic.fee', 'classification_id', 'Fees')
    faculty_ids = fields.One2many('quickledger.faculty', 'classification_id', 'Faculties')


class Faculty(models.Model):
    _name = "quickledger.faculty"
    _description = "Faculty"
    _order = "name"

    school_id = fields.Many2one('quickledger.school', "School")
    code = fields.Char("Code", required=False)
    name = fields.Char("Name", required=True)
    department_ids = fields.One2many('quickledger.department', 'faculty_id', 'Add Department')
    programme_ids = fields.One2many('quickledger.programme', 'faculty_id', 'Programmes')
    fee_ids = fields.One2many(related='classification_id.fee_ids', string='Fees', readonly=True)
    payment_type_ids = fields.Many2many(comodel_name='payment.type', string="Payment Types")
    classification_id = fields.Many2one('quickledger.faculty.classification', "Faculty Classification", required=True)
    
    def _get_applicable_fees_by_diploma(self, diploma_type_id):
        for faculty in self:
            return faculty.fee_ids.filtered(lambda f: f.diploma_type_id.id == diploma_type_id)
        return []
    
    @api.model
    def create(self, vals):
        _logger.info(f"Faculty create() called with {vals}")
        domain = ['|',('name', '=', str(vals['name']).strip()),
                  ('name', '=ilike', str(vals['name']).strip())]
        
        previous_entry = self.env['quickledger.faculty'].search(domain)
        
        if previous_entry:
            _logger(f"Returned Previous Entry {previous_entry.name} {previous_entry.code}")
            return previous_entry
        else:
            return super(Faculty, self).create(vals)


class School(models.Model):
    """ Defining School Information """
    _description = 'School Information'
    _name = 'quickledger.school'
    _inherits = {'res.company': 'company_id'}
    
    @api.model
    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'NGN')], limit=1)

    company_id = fields.Many2one('res.company', 'Company', ondelete="cascade", required=True)
    code = fields.Char('Code', size=20, required=True, index=1)
    faculty_ids = fields.One2many('quickledger.faculty', 'school_id', 'Faculties')
    grading_scheme_id = fields.Many2one('quickledger.grading.scheme', 'Grading Scheme')
    honour_scheme_id = fields.Many2one('quickledger.honour.scheme', 'Honour Scheme')
    fee_ids = fields.One2many('academic.fee', 'school_id', 'Fees')
    # currency_id = fields.Many2one('res.currency', readonly=True, default=_default_currency)


class AcademicLevel(models.Model):
    """ Defining Level Information """
    _description = 'Academic Level Information'
    _name = 'quickledger.level'
    _order = "name"

    sequence = fields.Integer('Sequence', default=1, required=True)
    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=20, required=True)
    next_class_id = fields.Many2one('quickledger.level', "Next Class")
    previous_class_id = fields.Many2one('quickledger.level', "Previous Class")
    type_id = fields.Many2one('quickledger.diploma.type', "Degree Type", required=True)
    description = fields.Text('Description')
    sequence = fields.Integer(string='Sequence')


class AcademicSession(models.Model):
    """ Defining Level Information """
    _description = 'Academic Session Information'
    _name = 'academic.session'
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1, required=True)
    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=20, required=True)
    description = fields.Text('Description')
    date_start = fields.Date("Start Date")
    date_end = fields.Date("End Date")


class Student(models.Model):
    """Defining a subject """
    _name = "quickledger.student"
    _description = "Students"
    
    @api.model
    def _default_country(self):
        return self.env['res.country'].search([('name', '=', 'Nigeria')], limit=1)

    name = fields.Char('Name', size=128, required=True)
    matriculation_number = fields.Char('Registration. No', size=64, help='Registration No.', required=True)
    application_number = fields.Char('Application. No', size=64, help='Application No.')
    phone = fields.Char('Phone Number', size=64)
    email = fields.Char('Email', size=32)
    image = fields.Binary(
        "Photograph", attachment=True,
        help="This field holds the image used as photo for the student, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo", attachment=True,
        help="Medium-sized photo of the student. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo", attachment=True,
        help="Small-sized photo of the student. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    programme_id = fields.Many2one('quickledger.programme', "Programme", required=True)
    department_id = fields.Many2one(related='programme_id.department_id', store=True, readonly=True,
                                    string="Department")
    entry_status_id = fields.Many2one(related='programme_id.entry_status_id', store=True, readonly=True,
                                    string="Entry Status")
    diploma_id = fields.Many2one(related='programme_id.diploma_id', string="Degree", store=True, readonly=True)
    faculty_id = fields.Many2one(related='programme_id.faculty_id', string="Faculty", store=True, readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School')
    balance_brought_forward = fields.Monetary(currency_field='currency_id', string="Balance B/F")
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    ledger_id = fields.Many2one(comodel_name="student.ledger", string="Ledger", readonly=True, ondelete='cascade')
    result_book_ids = fields.One2many('student.result', 'student_id', 'Result Book', readonly=True)
    result_ids = fields.One2many('student.result.entry', 'student_id', 'Results')
    approved_result_ids = fields.One2many('student.result.entry', string='Approved Results',
                                          compute='_compute_approved_results', readonly=True)
    classification_id = fields.Many2one(string="Classification", related="department_id.classification_id", readonly=True)
    number_of_certificates = fields.Selection(string="Number of Certicates", 
                                      selection=[('1', '1'), ('2', '2')], default="1")
    
    _sql_constraints = [
        ('student_registration_uniq',
         'UNIQUE (matriculation_number)',
         'Student Matriculation number already exist!')]

    def _create_student_result(self, student):
        StudentResultBook = self.env['student.result']
        vals = {'student_id': student.id, 'programme_id': student.programme_id.id}
        result_book = StudentResultBook.create(vals)
        return result_book
    
    def _create_ledger(self, student):
        vals = {'student_id': student.id}
        if student.balance_brought_forward > 0:
            vals['balance_brought_forward'] = -1 * student.balance_brought_forward
        else:
            vals['balance_brought_forward'] = student.balance_brought_forward

        StudentLedger = self.env['student.ledger']
        ledger = StudentLedger.create(vals)
        return ledger

    def write(self, vals):
        return super(Student, self).write(vals)

    @api.model
    def create(self, vals):
        vals['name'] = str(vals['name']).title()
        new_record = super(Student, self).create(vals)
        ledger = self._create_ledger(new_record)
        new_record.write({'ledger_id': ledger.id})
        result_book = self._create_student_result(new_record)
        new_record.write({'result_book_ids': [(4, result_book.id)]})
        return new_record

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.matriculation_number} {record.name}"
            result.append((record.id, name))
        return result

    def _compute_approved_results(self):
        for record in self:
            record.approved_result_ids = record.mapped('result_ids').filtered(
                lambda result: result.status == 'Approved')


class Honour(models.Model):
    _name = 'quickledger.honour'
    _description = 'Academic Honors'

    name = fields.Char('Honour', size=64, required=True)
    description = fields.Char('Description', size=250)
    upper_bound = fields.Float('To', required=True)
    lower_bound = fields.Float('From', required=True)
    honour_scheme_id = fields.Many2one('quickledger.honour.scheme', 'Honour Scheme')

    @api.model
    def compute_gpa(self, results):
        """ This will calculates the cumulative grade point average(CGPA) given a domain"""
        approved_results = results.filtered(lambda r: r.status == 'Approved')
        total_credits = sum([result.units for result in approved_results])
        total_points = sum([result.points * result.units for result in approved_results])
        if total_points:
            cgpa_in_str = str(total_points / total_credits)
            cgpa_in_float = float(cgpa_in_str[0:4])
            return cgpa_in_float
        else:
            return 0.00


class Diploma(models.Model):
    _name = 'quickledger.diploma'
    _description = "Degree"
    _order = 'name desc'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(size=130, string='Description')
    department_ids = fields.Many2many(comodel_name='quickledger.department', string='Departments')
    type_id = fields.Many2one('quickledger.diploma.type', 'Degree Type', required=True)


class DiplomaType(models.Model):
    _name = 'quickledger.diploma.type'
    _description = "Degree Type"
    _order = 'name desc'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(size=130, string='Description')
    diploma_ids = fields.One2many('quickledger.diploma', 'type_id', 'Degrees')


class GradingScheme(models.Model):
    _name = 'quickledger.grading.scheme'
    _description = 'Academic Grading Scheme'

    name = fields.Char('Name', size=64, required=True)
    description = fields.Text('Description')
    grading_ids = fields.One2many('quickledger.grade', 'grading_scheme_id', 'Gradings')

    def get_grade(self, score):
        res = 0
        for scheme in self:
            for grade in scheme.grading_ids:
                if grade.min_grade <= score <= grade.max_grade:
                    res = grade.id
                    break
        return res


class HonourScheme(models.Model):
    _name = 'quickledger.honour.scheme'
    _description = 'Academic Honors Scheme'
    name = fields.Char('Grade', size=128, required=True)
    description = fields.Text('Description')
    options = fields.Selection(string="Options",
                               selection=[
                                   ('allow_grade_replacement',
                                    'Allow Grades Replacement'),
                                   ('no_allow_replacement',
                                    'No Grades Replacement'),
                               ])
    honour_ids = fields.One2many(
        'quickledger.honour', 'honour_scheme_id', 'Honour Scheme')


class Grade(models.Model):
    _name = 'quickledger.grade'
    _description = 'Academic Grade'
    _order = 'name asc'

    name = fields.Char('Grade', size=64, required=True)
    point = fields.Float(required=True)
    description = fields.Char('Description', size=250)
    min_grade = fields.Float('Lower Bound', required=True)
    max_grade = fields.Float('Upper Bound', required=True)
    is_pass_mark = fields.Boolean('Is Pass Mark?')
    grading_scheme_id = fields.Many2one('quickledger.grading.scheme', 'Grading Scheme')


class AcademicProgrammeOption(models.Model):
    _name = "quickledger.programme.option"
    _description = "Programme Option"
    _order = 'name asc'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    programme_id = fields.Many2one('quickledger.programme', string='Programme', required=True)


class ProgrammeCourse(models.Model):
    _name = "programme.course"
    _description = "Course"
    _order = 'name, code, semester_id'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')
    semester_id = fields.Many2one('quickledger.semester', 'Semester', required=True)
    diploma_id = fields.Many2one('quickledger.diploma', 'Degree', required=True)
    entry_ids = fields.One2many('programme.course.entry', 'course_id', 'Programmes')
    lecturer_ids = fields.Many2many(comodel_name='quickledger.lecturer', string='Lecturers')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code}"
            result.append((record.id, name))
        return result


class ProgrammeCourseEntry(models.Model):
    _name = "programme.course.entry"
    _description = "Course"
    _order = 'level_id,semester_id,name,code'

    name = fields.Char(related="course_id.name", string='Name', readonly=True, store=True)
    code = fields.Char(related="course_id.code", string='Code', readonly=True, store=True)
    semester_id = fields.Many2one(related="course_id.semester_id", string='Semester', readonly=True, store=True)
    units = fields.Integer("Units", required=True, default=1)
    course_id = fields.Many2one('programme.course', 'Prerequisite')
    programme_id = fields.Many2one('quickledger.programme', 'Department')
    level_id = fields.Many2one('quickledger.level', 'Level', required=True)
    option_id = fields.Many2one('quickledger.programme.option', 'Option', required=False)

    def name_get(self):
        result = []
        for record in self:
            name = "{record.code}"
            result.append((record.id, name))
        return result


class StudentResultBook(models.Model):
    _description = 'Collection Student Academic Record'
    _name = 'student.result'
    _order = 'student_id,programme_id'
    _inherit = ['mail.thread']

    _sql_constraints = [
        ('student_result_book_uniq',
         'UNIQUE (student_id)',
         'Student can only have one Result Book!')]

    student_id = fields.Many2one('quickledger.student', 'Student', required=True)
    programme_id = fields.Many2one(related='student_id.programme_id', string='Programme', store=True)
    entry_ids = fields.One2many(comodel_name='student.result.entry', inverse_name='student_result_id', string='Entries',
                                required=False, track_visibility="always")
    outstanding_result_ids = fields.Many2many(comodel_name='student.result.entry',
                                              compute='_compute_outstanding_results', string="Outstanding Results",
                                              readonly=True)
    outstanding_course_ids = fields.Many2many(comodel_name='programme.course.entry',
                                              compute='_compute_outstanding_courses', string="Outstanding Courses",
                                              readonly=True)
    cgpa = fields.Float(string="CGPA", readonly=True, track_visibility="always")
    honours_id = fields.Many2one(comodel_name='quickledger.honour', compute='_compute_honour', readonly=True,
                                 store=True,
                                 string="Honours", track_visibility="always")
    approved_result_ids = fields.One2many('student.result.entry', string='Approved Results',
                                          compute='_compute_approved_results', readonly=True)
    registration_id = fields.Many2one('student.registration', 'Registration')

    @api.depends('entry_ids')
    def _compute_outstanding_results(self):
        for record in self:
            res = []
            failed_courses = record.entry_ids.filtered(lambda c: c.grade_id.is_pass_mark == False and
                                                                 c.status == 'Approved')
            passed_courses = record.entry_ids.filtered(lambda c: c.grade_id.is_pass_mark == True)
            for failed_course in failed_courses:
                if failed_course.id not in passed_courses.ids:
                    res.append(failed_course.id)

            record.outstanding_result_ids = res

    @api.depends('entry_ids')
    def _compute_outstanding_courses(self):
        for record in self:
            record.outstanding_course_ids = [entry.course_id.id for entry in record.outstanding_result_ids]

    @api.depends('entry_ids')
    def _compute_approved_results(self):
        for record in self:
            record.approved_result_ids = record.mapped('entry_ids').filtered(lambda result: result.status == 'Approved')

    def compute_cgpa(self):
        """ This will calculates the cumulative grade point average(CGPA) given a domain"""
        for record in self:
            approved_results = record.entry_ids.filtered(lambda r: r.status == 'Approved')
            cgpa = self.env['quickledger.honour'].compute_gpa(approved_results)

            return cgpa

    def action_recompute_cgpa(self):
        for record in self:
            if record.entry_ids:
                cgpa = record.compute_cgpa()
                record.write({'cgpa': cgpa})
                record._compute_honour()

    @api.model
    def write(self, values):
        # Add code here
        if values.get('entry_ids', False):
            self.action_recompute_cgpa()
        return super(StudentResultBook, self).write(values)

    @api.depends('cgpa')
    def _compute_honour(self):
        for record in self:
            if record.cgpa > 0.00:
                honours = self.env['quickledger.honour'].search([])
                honour = honours.filtered(lambda h: h.lower_bound <= record.cgpa <= h.upper_bound)
                record.honours_id = honour[0]

    def name_get(self):
        result = []
        for record in self:
            name = "{0} - {1} Results".format(record.student_id.matriculation_number, record.student_id.name)
            result.append((record.id, name))
        return result
    
   
class StudentRegistrationEntry(models.Model):
    _description = 'Student Course Registration Entry'
    _name = 'student.registration.entry'
    _order = 'level_id,semester_id'

    _sql_constraints = [
        ('registration_entry_course_uniq',
         'UNIQUE (student_id, course_id, session_id)',
         'Student, Course and Session must be unique!')]

    registration_id = fields.Many2one('student.registration', 'Registration', required=True, ondelete='cascade')
    student_id = fields.Many2one(related='registration_id.student_id', string='Student', store=True, readonly=True)
    programme_id = fields.Many2one(related='registration_id.programme_id', string='Programme', store=True,
                                   readonly=True)
    level_id = fields.Many2one(related='course_id.level_id', string='Level', store=True, readonly=True)
    session_id = fields.Many2one(related='registration_id.session_id', string='Session', store=True, readonly=True)
    course_id = fields.Many2one('programme.course.entry', 'Course', required=True, ondelete='cascade')
    units = fields.Integer(related='course_id.units', string='Units', readonly=True)
    code = fields.Char(related='course_id.code', string='Code', readonly=True)
    name = fields.Char(related='course_id.name', string='Name', readonly=True)
    semester_id = fields.Many2one(related='course_id.semester_id', string='Semester', readonly=True, store=True, )
    is_brought_forward = fields.Boolean('Brought Forward')

    def unlink(self):
        domain = [('registration_id', '=', self.registration_id.id), ('course_id', '=', self.course_id.id)]
        resultEntry = self.env['student.result.entry'].search(domain)
        resultEntry.unlink()
        result = super(StudentRegistrationEntry, self).unlink()

        return result


class StudentRegistration(models.Model):
    _description = 'Student Registration'
    _name = 'student.registration'
    _inherit = ["mail.thread"]
    _rec_name = 'student_id'

    _sql_constraints = [
        ('registration_course_uniq',
         'UNIQUE (student_id, session_id)',
         'Student can only register once for session!')]

    @api.model
    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())
    
    @api.model
    def _default_semester(self):
        return self.env['quickledger.semester'].search([('code', '=', '1st')], limit=1)


    entry_date = fields.Date('Date', required=True, default=_get_default_date)
    student_id = fields.Many2one('quickledger.student', 'Student', required=True)
    matriculation_number = fields.Char(related="student_id.matriculation_number", readonly=True, store=True)
    ledger_entry_id = fields.Many2one('student.ledger.entry', string='Ledger', readonly=True)
    level_id = fields.Many2one('quickledger.level', 'Level', required=True)
    receipt_number = fields.Char('Receipt #', states={'Approved': [('readonly', True)], 'Closed': [('readonly', True)]})
    fee_entry_ids = fields.One2many('academic.fee.entry', 'registration_id', 'Fee Entries', )
    session_id = fields.Many2one('academic.session', 'Session', required=True)
    semester_id = fields.Many2one('quickledger.semester', 'Semester', default=_default_semester)
    programme_id = fields.Many2one('quickledger.programme', string="Programme", required=True)
    faculty_id = fields.Many2one(related='programme_id.faculty_id', string="Faculty", store=True)
    department_id = fields.Many2one(related='programme_id.department_id', string="Department", store=True)
    diploma_id = fields.Many2one(related='programme_id.diploma_id', string="Diploma", store=True, readonly=True)
    total_credit_units = fields.Float(compute='_compute_total_credit_units', store=True)
    total_charges = fields.Monetary(currency_field='currency_id', compute='_compute_total_charges', string="Total Charges/Fees", readonly=True, store=True)
    currency_id = fields.Many2one('res.currency', related='ledger_entry_id.currency_id', readonly=True)

    state = fields.Selection(string="Status",
                             selection=[
                                 ('New', 'New'),
                                 ('Approved', 'Approved'),
                                 ('Closed', 'Closed')
                             ], default='New', track_visibility="onchange", )
    entry_ids = fields.One2many('student.registration.entry', 'registration_id', 'Courses')
    entry_current_ids = fields.Many2many(comodel_name='student.registration.entry',
                                         compute='_compute_current_courses', string="Current Courses Forward",
                                         readonly=True)
    entry_brought_forward_ids = fields.Many2many(comodel_name='student.registration.entry',
                                                 compute='_compute_courses_brought_forward',
                                                 string="Courses Brought Forward", readonly=True)
    result_ids = fields.One2many('student.result.entry', 'registration_id', 'Results')
    gpa = fields.Float(string="Semester GPA", readonly=True, track_visibility="onchange")
    approved_result_ids = fields.One2many('student.result.entry', string='Approved Results',
                                          compute='_compute_approved_results', readonly=True)


    @api.onchange('programme_id')
    def programme_id_changed(self):
        domain = {}
        if self.programme_id:
            if self.programme_id.duration == 4:
                domain = {'level_id':['|','|','|','|',
                                      ('sequence','=','1'),
                                      ('sequence','=','2'),
                                      ('sequence','=','3'),
                                      ('sequence','=','4'),
                                      ('sequence','=','5')]}
            elif self.programme_id.duration == 5:
                domain = {'level_id':['|','|','|','|','|','|',
                                      ('sequence','=','1'),
                                      ('sequence','=','2'),
                                      ('sequence','=','3'),
                                      ('sequence','=','4'),
                                      ('sequence','=','5'),
                                      ('sequence','=','6'),
                                      ('sequence','=','7')]}
            elif self.programme_id.duration == 6:
                domain = {'level_id':['|','|','|','|','|','|',
                                      ('sequence','=','1'),
                                      ('sequence','=','2'),
                                      ('sequence','=','3'),
                                      ('sequence','=','4'),
                                      ('sequence','=','5'),
                                      ('sequence','=','6'),
                                      ('sequence','=','7')]}
            else:
                domain = {'level_id':['|','|','|','|','|','|'
                                      ('sequence','=','1'),
                                      ('sequence','=','2'),
                                      ('sequence','=','3'),
                                      ('sequence','=','4'),
                                      ('sequence','=','5'),
                                      ('sequence','=','6'),
                                      ('sequence','=','7')]}            
        return {'domain': domain}

    def _compute_approved_results(self):
        for record in self:
            record.approved_result_ids = record.mapped('result_ids').filtered(
                lambda result: result.status == 'Approved')

    def action_recompute_cgpa(self):
        for record in self:
            if record.result_ids:
                approved_results = record.approved_result_ids
                gpa = self.env['quickledger.honour'].compute_gpa(approved_results)
                record.write({'gpa': gpa})

    def action_approve_registration(self):
        self.write({'state': 'Approved'})

    def action_close_registration(self):
        results = self.result_ids.filtered(lambda r: r.status == 'Approved')
        gpa = self.env['quickledger.honour'].compute_gpa(results)
        self.write({'state': 'Closed', 'gpa': gpa})

    @api.depends('result_ids')
    def _compute_results(self):
        for record in self:
            if record.entry_ids:
                results = self.env["student.result.entry"].search([("session_id", "=", record.session_id.id),
                                                                   ("student_id", "=", record.student_id.id),
                                                                   ("semester_id", "=", record.semester_id.id)])
                record.result_ids = results
    
    @api.depends('entry_ids')         
    def _compute_total_credit_units(self):
         for record in self:
                if record.entry_ids:
                    record.total_credit_units = sum([entry.units for entry in record.entry_ids])
                else:
                    record.total_credit_units = 0
                    
    @api.depends('fee_entry_ids')         
    def _compute_total_charges(self):
         for record in self:
                if record.fee_entry_ids:
                    record.total_charges = sum([entry.amount_due for entry in record.fee_entry_ids])
                else:
                    record.total_charges = 0.00
                
    def name_get(self):
        result = []
        for record in self:
            name = "{0} - {1}".format(record.student_id.matriculation_number, record.student_id.name)
            result.append((record.id, name))
        return result

    @api.depends('entry_ids')
    def _compute_courses_brought_forward(self):
        for record in self:
            record.entry_brought_forward_ids = record.entry_ids.filtered(lambda c: c.is_brought_forward == True)

    @api.depends('entry_ids')
    def _compute_current_courses(self):
        for record in self:
            record.entry_current_ids = record.entry_ids.filtered(lambda c: c.is_brought_forward == False)

    def get_result_for_course(self, course_id, ):
        return self.env['student.result.entry'].search([('student_id', '=', self.student_id.id),
                                                        ('course_id', '=', course_id),
                                                        ('semester_id', '=', self.semester_id.id),
                                                        ('session_id', '=', self.session_id.id)])

    def add_student_result_entry(self, student_result, course_id, scores):
        entry = self.get_result_for_course(course_id)
        if entry:
            entry.write({'ca_score': scores.get('exam', 0.00),
                         'practicals_score': scores.get('practicals', 0.00),
                         'test_score': scores.get('test', 0.00)})
        else:
            vals = {'student_result_id': student_result.id,
                    'student_id': self.student_id.id,
                    'course_id': course_id,
                    'semester_id': self.semester_id.id,
                    'level_id': self.level_id.id,
                    'session_id': self.session_id.id,
                    'registration_id': self.id,
                    'ca_score': scores.get('exam', 0.00),
                    'practicals_score': scores.get('practicals', 0.00),
                    'test_score': scores.get('test', 0.00),
                    'status': 'Approved'}
            entry = self.env['student.result.entry'].create(vals)
            # Adds result to Student Results Collection
            self.student_id.write({'result_ids': [(4, entry.id)]})
        return entry
    
    def _update_balance_carried_forward(self):
         StudentLedger = self.env['student.ledger']
         ledger = StudentLedger.search([('student_id', '=', self.student_id.id)])
         balance = ledger.total_balance
         ledger.write({'balance_carried_forward' : ledger.total_balance})
         
    def _update_total_charges(self):
         StudentLedger = self.env['student.ledger']
         ledger = StudentLedger.search([('student_id', '=', self.student_id.id)])
         _logger.info(f"Total Charges ::: {self.total_charges}")
         ledger.write({'current_charges' : self.total_charges})
 
    
    def _create_fee_entries(self):
        AcademicFeeEntry = self.env['academic.fee.entry']
        AcademicProgramme = self.env['quickledger.programme']
        StudentLedger = self.env['student.ledger']

        ledger = StudentLedger.search([('student_id', '=', self.student_id.id)])
        programme = AcademicProgramme.browse(self.programme_id.id)
        level_id = self.level_id.id
        all_fees = self.programme_id._get_applicable_fees_by_level(level_id)
        for fee in self.programme_id._get_applicable_fees_by_level(level_id):
            AcademicFeeEntry.create({'registration_id': self.id,
                                     'fee_id': fee.id, 
                                     'ledger_id': ledger.id})

        return True

    def _create_student_result_entries(self, student_result):
        vals = {}
        programme_id = self.programme_id.id
        semester_id = self.semester_id.id
        session_id = self.session_id.id
        level_id = self.level_id.id
        student = self.env['quickledger.student'].browse(student_result.student_id.id)
        courses = self._get_courses(programme_id, level_id, semester_id)
        _logger.info("Courses for the Semester ::: {}".format(courses))
        for course in courses:
            vals['student_result_id'] = student_result.id
            vals['student_id'] = student.id
            vals['course_id'] = course.id
            vals['semester_id'] = semester_id
            vals['level_id'] = level_id
            vals['session_id'] = session_id
            vals['registration_id'] = self.id

            entry = self.env['student.result.entry'].create(vals)
            # Adds result to Student Results Collection
            student.write({'result_ids': [(4, entry.id)]})

        return True

    def _create_course_entries(self):
        level_id = self.level_id.id
        semester_id = self.semester_id.id
        programme_id = self.programme_id.id
        student_id = self.student_id.id
        #  option_id = registration.student_id.option_id.id if registration.student_id.option_id else None
        courses = self._get_courses(programme_id, level_id, semester_id)
        outstanding_course_ids = self._get_outstanding_courses(student_id, semester_id)

        for course in courses:
            StudentRegistrationEntry.create({'registration_id': self.id, 'course_id': course.id})

        for course_id in outstanding_course_ids:
            self.env['student.registration.entry'].create({'registration_id': self.id,
                                                           'course_id': course_id, 'is_brought_forward': True})
        return True

    def get_course_entry(self, course_id, ):
        return self.env['student.registration.entry'].search([('registration_id', '=', self.id),
                                                              ('course_id', '=', course_id)])

    def add_course_entry(self, course_id, is_brought_forward=False):
        entry = self.get_course_entry(course_id)
        if entry:
            return entry
        else:
            return self.env['student.registration.entry'].create({'registration_id': self.id,
                                                                  'course_id': course_id,
                                                                  'is_brought_forward': is_brought_forward})

    def _get_courses(self, programme_id, level_id, semester_id):
        courses = []
        domain = [('level_id', '=', level_id), ('semester_id', '=', semester_id), ('programme_id', '=', programme_id)]
        all_courses = self.env['programme.course.entry'].search(domain)
        _logger.info("All available courses {}".format(all_courses))
        # programme = self.env['quickledger.programme'].browse(programme_id)
        for course in all_courses:  # programme.course_ids.filtered(lambda c: c.semester_id.id == semester_id and c.level_id.id == level_id):
            courses.append(course)
        return courses

    def _get_outstanding_courses(self, student_id, semester_id):
        results = self.env['student.result'].search([('student_id', '=', student_id)])
        return results.outstanding_course_ids.filtered(lambda c: c.semester_id.id == semester_id).ids

    @api.model
    def create(self, vals):
        is_legacy = False
        if vals.get('is_legacy', False):
            is_legacy = True
            vals.pop('is_legacy')
        registration = super(StudentRegistration, self).create(vals)
        student_result = self.env['student.result'].browse(vals['student_id'])
        if is_legacy:
            return registration
        # else:
            # self._create_student_result_entries(student_result)
        #     self._create_course_entries()
            
        # if registration.semester_id.code == '1st':
        registration._update_balance_carried_forward()
        registration._create_fee_entries()
        registration._update_total_charges()
      
        return registration

    def write(self, vals):
        result = super(StudentRegistration, self).write(vals)
        return result


class StudentResultBookEntry(models.Model):
    _description = 'Student Academic Record'
    _name = 'student.result.entry'
    _order = 'entry_date, session_id, semester_id, level_id'

    _sql_constraints = [
        ('student_result_uniq',
         'UNIQUE (student_id, session_id, course_id, semester_id)',
         'Student can only register a particular once a session!')]

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    @api.model
    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    entry_date = fields.Date('Date', default=_get_default_date)
    student_id = fields.Many2one(comodel_name='quickledger.student', string='Student')
    programme_id = fields.Many2one(related='student_id.programme_id', store=True, string='Programme', readonly=True)
    reg_number = fields.Char(related='student_id.matriculation_number', store=True, string='Reg #', readonly=True)
    student_result_id = fields.Many2one('student.result', 'Result Book')
    session_id = fields.Many2one('academic.session', 'Session')
    semester_id = fields.Many2one(comodel_name='quickledger.semester', string='Semester', readonly=True)
    course_id = fields.Many2one(comodel_name='programme.course.entry', string='Course', readonly=True)
    level_id = fields.Many2one(comodel_name='quickledger.level', string='Level', readonly=True)
    course_name = fields.Char(related="course_id.name", string='Course Name', readonly=True, store=True)
    course_code = fields.Char(related="course_id.code", string='Course Code', readonly=True, store=True)
    units = fields.Integer(related='course_id.units', string='Units', readonly=True, store=True)
    remarks = fields.Text('Remarks', track_visibility="all")
    gpa = fields.Float("GPA", compute='_compute_gpa',  store=True)
    ca_score = fields.Float('Examination Score', track_visibility="onchange")
    test_score = fields.Float('Test Score', track_visibility="onchange")
    points = fields.Float(related="grade_id.point", string='Points', readonly=True, store=True)
    points_obtained = fields.Float(string='Points Obtained', readonly=True, compute='_compute_points_obtained',
                                   store=True)
    practicals_score = fields.Float('Practicals Score', track_visibility="onchange")
    score = fields.Float(compute='_compute_total_score', string="Total", store=True, readonly=True,
                         track_visibility="onchange")
    grade_id = fields.Many2one(comodel_name='quickledger.grade', compute='_compute_grade',
                               string="Grade", readonly=True, store=True, track_visibility="onchange")
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    is_pass_mark = fields.Boolean(compute='_compute_is_pass_mark', string="Is Pass Mark?", store=True, readonly=True,
                                  track_visibility="onchange")
    registration_id = fields.Many2one('student.registration', 'Registration')
    status = fields.Selection(
        string="Status",
        selection=[
            ('Draft', 'Draft'),
            ('Pending', 'Pending Approval'),
            ('Approved', 'Approved')], default='Draft')

    def name_get(self):
        result = []
        for record in self:
            name = "{0} {1} :: {2}".format(record.course_id.code, record.score, record.grade_id.name)
            result.append((record.id, name))
        return result

    def write(self, vals):
        if 'score' in vals or 'ca_score' in vals or 'test_score' in vals or 'practicals_score' in vals or 'status' in vals:
            if self.status == "Draft":
                vals['status'] = 'Pending'
            else:
                points = self.grade_id.point * self.units
                vals['points_obtained'] = points

        return super(StudentResultBookEntry, self).write(vals)

    @api.constrains('practicals_score', 'test_score', 'ca_score')
    def _check_score_lesser_than_100(self):
        for record in self:
            if record.score > 100:
                raise exceptions.ValidationError('Total Score cannot be greater than 100')

    @api.constrains('practicals_score')
    def _check_practicals_score_lesser_zero(self):
        for record in self:
            if record.practicals_score < 0:
                raise exceptions.ValidationError('Practical Score cannot be lesser than 0')

    @api.constrains('practicals_score')
    def _check_practicals_score_lesser_zero(self):
        for record in self:
            if record.practicals_score < 0:
                raise exceptions.ValidationError('Practical Score cannot be lesser than 0')

    @api.constrains('test_score')
    def _check_test_score_lesser_zero(self):
        for record in self:
            if record.test_score < 0:
                raise exceptions.ValidationError('Test Score cannot be lesser than 0')

    @api.constrains('score')
    def _check_score(self):
        for record in self:
            if record.score > 100:
                raise exceptions.ValidationError('Score cannot be greater than 100')

    @api.depends('ca_score', 'practicals_score', 'test_score')
    def _compute_grade(self):
        for record in self:
            grading_scheme = record.school_id.grading_scheme_id
            total_score = record.ca_score + record.practicals_score + record.test_score
            record.grade_id = grading_scheme.get_grade(total_score)

    @api.depends('ca_score', 'practicals_score', 'test_score')
    def _compute_is_pass_mark(self):
        for record in self:
            grading_scheme = record.school_id.grading_scheme_id
            total_score = record.ca_score + record.practicals_score + record.test_score
            grade_id = grading_scheme.get_grade(total_score)
            grade = self.env['quickledger.grade'].browse(grade_id)
            record.is_pass_mark = grade.is_pass_mark

    @api.depends('ca_score', 'practicals_score', 'test_score')
    def _compute_points_obtained(self):
        for record in self:
            if record.grade_id:
                record.points_obtained = record.grade_id.point * record.units

    @api.depends('ca_score', 'practicals_score', 'test_score')
    def _compute_total_score(self):
        for record in self:
            total_score = record.ca_score + record.practicals_score + record.test_score
            record.score = total_score
            
    @api.depends('registration_id.entry_ids')
    def _compute_gpa(self):
        for record in self:
            if record.registration_id and record.registration_id.entry_ids:
                if record.registration_id.total_credit_units:
                    record.gpa = record.points_obtained/record.registration_id.total_credit_units


class StudentLedger(models.Model):
    _name = 'student.ledger'
    _description = 'Student Financial Record'
    _inherit = ['portal.mixin']

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    student_id = fields.Many2one(comodel_name='quickledger.student', string='Student', required=True)
    image = fields.Binary(string='Passport', related="student_id.image", stored=True)
    matriculation_number = fields.Char(related="student_id.matriculation_number", readonly=True, store=True)
    programme_id = fields.Many2one(related='student_id.programme_id', string='Programme', store=True, readonly=True)
    total_amount_paid = fields.Monetary(compute='_compute_amount_paid', currency_field='currency_id',
                                        string="Total Amount Paid", store=True, readonly=True)
    total_amount_due = fields.Monetary(compute='_compute_amount_due', currency_field='currency_id',
                                       string="Total Amount Due", store=True, readonly=True)
    total_balance = fields.Monetary(compute='_compute_balance', currency_field='currency_id', string="Amount Outstanding",
                                    store=True, readonly=True)
    balance_brought_forward = fields.Monetary(currency_field='currency_id', related="student_id.balance_brought_forward",
                                               string="Balance B/F", readonly=True)
    opening_balance = fields.Monetary(currency_field='currency_id', string="Opening Debit Balance", readonly=True)
    balance_carried_forward = fields.Monetary(currency_field='currency_id', string="Previous Debit Balance")
    entry_ids = fields.One2many(comodel_name='student.ledger.entry', inverse_name='ledger_id', string='Entries')
    fee_entry_ids = fields.One2many(comodel_name='academic.fee.entry', inverse_name='ledger_id', string='Fees')
    payment_entry_ids = fields.One2many(comodel_name='academic.payment.entry', inverse_name='ledger_id',
                                        string='Payments')
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    outstanding_fee_ids = fields.Many2many(comodel_name='academic.fee.entry', compute='_compute_outstanding_fees',
                                           string="Outstanding Payments", readonly=True)
    paid_fee_ids = fields.Many2many(comodel_name='academic.fee.entry', compute='_compute_paid_fees',
                                    string="Completed Payments", readonly=True)
    current_charges = fields.Monetary(currency_field='currency_id', string="Current Charges/Fees", readonly=True)
    
    @api.model
    def create(self, vals):
        student = self.env['quickledger.student'].browse(vals['student_id'])
        vals['opening_balance'] = student.balance_brought_forward
        return super(StudentLedger, self).create(vals)
    
    def preview_ledger(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _compute_access_url(self):
        super(StudentLedger, self)._compute_access_url()
        for ledger in self:
            ledger.access_url = '/my/studentledger/%s' % ledger.id

    
    def action_ledger_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('unizik', 'email_unizik_ledger_reminder_mail')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'student.ledger',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.depends('fee_entry_ids.amount_due', 'payment_entry_ids')
    def _compute_outstanding_fees(self):
        for record in self:
            fee_ids = []
            for fee in record.fee_entry_ids:
                if fee.amount_due > fee.amount_paid:
                    fee_ids.append(fee.id)
            record.update({'outstanding_fee_ids': [(6, 0, fee_ids)]})

    @api.depends('fee_entry_ids.amount_due', 'payment_entry_ids')
    def _compute_paid_fees(self):
        for record in self:
            fee_ids = []
            for fee in record.fee_entry_ids:
                if fee.amount_paid > 0.00:
                    fee_ids.append(fee.id)
            record.update({'paid_fee_ids': [(6, 0, fee_ids)]})

    @api.depends('payment_entry_ids')
    def _compute_amount_paid(self):
        for record in self:
            record.total_amount_paid = sum([payment.amount for payment in record.payment_entry_ids])

    @api.depends('fee_entry_ids.balance', 'payment_entry_ids')
    def _compute_balance(self):
        for record in self:
            balance = abs(record.balance_brought_forward) + sum([fee.balance for fee in record.fee_entry_ids])
            # amount_paid = sum([payment.amount for payment in record.payment_entry_ids])
            record.total_balance = balance

    @api.depends('fee_entry_ids.amount_due')
    def _compute_amount_due(self):
        for record in self:
            total_amount_due = record.opening_balance + sum([fee.amount_due for fee in record.fee_entry_ids])
            record.total_amount_due = total_amount_due
    
    def name_get(self):
        result = []
        for record in self:
            name = "{0} - {1}".format(record.student_id.matriculation_number,
                                                        record.student_id.name)
            result.append((record.id, name))
        return result


class StudentLedgerEntry(models.Model):
    _name = 'student.ledger.entry'
    _description = 'Student Financial Record Entry'

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    ledger_id = fields.Many2one(comodel_name='student.ledger', string='Ledger', readonly=True)
    session_id = fields.Many2one(comodel_name='academic.session', string='Session', readonly=True)
    student_id = fields.Many2one(comodel_name='quickledger.student', string='Student', readonly=True)
    programme_id = fields.Many2one(related='student_id.programme_id', string='Programme', required=False, store=True,
                                   readonly=True)
    total_balance = fields.Monetary('Balance', currency_field='currency_id', readonly=True)
    total_amount_paid = fields.Monetary('Amount Paid', currency_field='currency_id', readonly=True)
    total_amount_due = fields.Monetary('Amount Due', currency_field='currency_id', readonly=True)
    fee_entry_ids = fields.One2many(comodel_name='academic.fee.entry', inverse_name='ledger_entry_id', string='Fees',
                                    required=False)
    registration_ids = fields.One2many(comodel_name='student.registration', inverse_name='ledger_entry_id',
                                       string='Entries', required=False)
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
  

class AcademicPaymentEntry(models.Model):
    """ Defining Academic Fee Information """
    _description = 'Academic Payment Entry Information'
    _name = 'academic.payment.entry'
    _order = "amount"

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    @api.model
    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    student_id = fields.Many2one('quickledger.student', 'Student', required=True, readonly=True)
    programme_id = fields.Many2one(related='student_id.programme_id', string='Programme', readonly=True, store=True)
    faculty_id = fields.Many2one(related='student_id.faculty_id', string='Faculty', readonly=True, store=True)
    department_id = fields.Many2one(related='student_id.faculty_id', string='Department', readonly=True, store=True)
    ledger_id = fields.Many2one('student.ledger', string='Ledger', readonly=True)
    level_id = fields.Many2one('quickledger.level', string='Level', required=True)
    session_id = fields.Many2one('academic.session', 'Session', required=True)
    amount = fields.Monetary('Amount Paid', currency_field='currency_id', readonly=True)
    teller_number = fields.Char('Teller #', readonly=True)
    payment_date = fields.Date('Payment Date', required=True, readonly=True, default=_get_default_date)
    bank_id = fields.Many2one('res.partner.bank', 'Bank', readonly=True)
    fee_ids = fields.Many2many('academic.fee.entry', 'payment_fee_rel', 'payment_id', 'fee_id', 'Fees', readonly=True)
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    balance = fields.Monetary(compute='_compute_balance', currency_field='currency_id', string="Balance", store=True,
                              readonly=True)
    amount_due = fields.Monetary(compute='_compute_amount_due', currency_field='currency_id', string="Amount Due",
                                 store=True, readonly=True)

    def name_get(self):
        result = []
        for record in self:
            name = "Payment by {0} {1} ".format(record.student_id.name, record.student_id.matriculation_number)
            result.append((record.id, name))
        return result

    @api.depends('amount')
    def _compute_balance(self):
        for record in self:
            record.balance = record.amount_due - record.amount

    @api.depends('amount')
    def _compute_amount_due(self):
        for record in self:
            record.amount_due = sum([fee.amount_due for fee in record.fee_ids])


class AcademicFeeEntry(models.Model):
    """ Defining Academic Fee Information """
    _description = 'Academic Fee Entry Information'
    _name = 'academic.fee.entry'
    _order = "amount_due"
    _rec_name = "description"

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)

    @api.model
    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    fee_id = fields.Many2one('academic.fee', 'Fee', required=True)
    description = fields.Text(related='fee_id.description', store=True, readonly=True)
    type_id = fields.Many2one(related='fee_id.type_id', string='Fee Type', store=True, readonly=True)
    amount_due = fields.Monetary(currency_field='currency_id', string='Amount Due', required=True)
    amount_paid = fields.Monetary('Amount Paid', currency_field='currency_id')
    entry_date = fields.Date('Entry Date', default=_get_default_date)
    payment_date = fields.Date('Payment Date', default=_get_default_date)
    registration_id = fields.Many2one('student.registration', 'Registration')
    ledger_entry_id = fields.Many2one('student.ledger.entry', string='Ledger Entry', readonly=True)
    ledger_id = fields.Many2one('student.ledger', string='Ledger', readonly=True)
    student_id = fields.Many2one(related='registration_id.student_id', store=True, readonly=True)
    programme_id = fields.Many2one(related='registration_id.programme_id', string='Programme', store=True,
                                   readonly=True)
    session_id = fields.Many2one(related='registration_id.session_id', store=True, string='Session', readonly=True)
    school_id = fields.Many2one(related='fee_id.school_id', store=True, readonly=True)
    level_id = fields.Many2one(related='registration_id.level_id', string='Level', store=True, readonly=True)
    payment_ids = fields.Many2many('academic.payment.entry', 'payment_fee_rel', 'fee_id', 'payment_id', 'Payments')
    balance = fields.Monetary(compute='_compute_balance', currency_field='currency_id', string="Balance", store=True,
                              readonly=True)
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    faculty_id = fields.Many2one(related='registration_id.faculty_id', string='Faculty', store=True, readonly=True)
    department_id = fields.Many2one(related='registration_id.department_id', string='Department', store=True, readonly=True)

    @api.model
    def create(self, vals):
        vals['amount_due'] = self.env['academic.fee'].browse(vals['fee_id']).amount
        fee = super(AcademicFeeEntry, self).create(vals)
        return fee
    
    def write(self, vals):
        fee = super(AcademicFeeEntry, self).write(vals)
        return fee

    def name_get(self):
        result = []
        for record in self:
            name = "{0}".format(record.type_id.name)
            result.append((record.id, name))
        return result

    @api.depends('amount_paid', 'amount_due')
    def _compute_balance(self):
        for record in self:
            record.balance = record.amount_due - record.amount_paid


class AcademicFee(models.Model):
    """ Defining Academic Fee Information """
    _description = 'Academic Fee Information'
    _name = 'academic.fee'
    _order = "level_id"

    @api.model
    def _default_school(self):
        return self.env['quickledger.school'].search([('name', '=', 'Nnamdi Azikiwe University')], limit=1)
    
    @api.model
    def _get_default_status(self):
        return self.env['quickledger.entry.status'].search([('name', '=', 'UME')], limit=1)


    amount = fields.Monetary('Amount', currency_field='currency_id')
    description = fields.Text('Description')
    type_id = fields.Many2one('payment.type', string='Type', required=True)
    name = fields.Char(related='type_id.name', string='Name', readonly=True, store=True)
    faculty_ids = fields.Many2many(comodel_name='quickledger.faculty', related="type_id.faculty_ids", readonly=True)
    level_ids = fields.Many2many(comodel_name='quickledger.level', related="type_id.level_ids", readonly=True)
    level_id = fields.Many2one('quickledger.level', string='Level')
    diploma_type_id = fields.Many2one(related='level_id.type_id', string='Degree Type', readonly=True)
    # faculty_id = fields.Many2one('quickledger.faculty', string='Faculty', required=False)
    school_id = fields.Many2one('quickledger.school', 'School')
    term_id = fields.Selection([("25", "At least 25% initial payment"),
                                ("50", "At least 50% initial payment"),
                                ("100", "A 100% paid once")], default="100",
                               string='Payment Terms')
    frequency = fields.Selection([('Semester', 'Semester'),
                                  ('Session', 'Session')], default="Session",
                                 string='Paid Per')
    currency_id = fields.Many2one('res.currency', related='school_id.currency_id', readonly=True)
    school_id = fields.Many2one('quickledger.school', 'School', default=_default_school)
    entry_type = fields.Many2one('quickledger.entry.status', string="Entry", default=_get_default_status)
    classification_id = fields.Many2one('quickledger.faculty.classification', string="Classification", required=True)
    number_of_certificates = fields.Selection(string="Number of Certicates", 
                                      selection=[('1', '1'), ('2', '2')], default="1")
    
    @api.model
    def create(self, vals):
        _logger.info(f"Vals :::: {vals}")
        domain = [('type_id', '=', vals['type_id']),
                  ('level_id', '=', vals['level_id']),
                  ('classification_id', '=', vals['classification_id'])]
        
        if vals.get('entry_type', False):
            domain.append(('entry_type', '=', vals['entry_type']))
        
        previous_fee = self.env['academic.fee'].search(domain)
        
        if previous_fee:
            return previous_fee
        else:
            return super(AcademicFee, self).create(vals)

    
    @api.constrains('amount')
    def _check_amount_greater_than_zero(self):
        for payment in self:
            if payment.amount <= 0:
                raise exceptions.ValidationError('Fee Amount must be greater than 0')
     
            
    @api.constrains('classification_id')
    def _check_invalid_fee_classification(self):
        for fee in self:
            pass
            # if fee.faculty_id:
            #    if fee.classification_id != fee.faculty_id.classification_id:
            #        raise exceptions.ValidationError('Invalid Fee Classification')


    def name_get(self):
        result = []
        for record in self:
            name = "{0}".format(record.type_id.name)
            result.append((record.id, name))
        return result

    @api.onchange('type_id')
    def type_id_changed(self):
        v = {}
        if self.type_id:
            for item in self.env['payment.type'].browse([self.type_id.id]):
                v['domain'] = item.domain

        return {'value': v}


class PaymentType(models.Model):
    _name = 'payment.type'
    _order = 'name'
    _description = "Payment Type"

    name = fields.Char("Name", size=64, required=True)
    code = fields.Char("Payment Code", help="A code to identify the payment",
                       default=lambda self: self.env['ir.sequence'].next_by_code('payment.type'),
                       readonly=True)
    description = fields.Text("Description")
    faculty_ids = fields.Many2many(comodel_name='quickledger.faculty', string="Faculties")
    level_ids = fields.Many2many(comodel_name='quickledger.level', string="Levels")
    has_components = fields.Boolean("Has Components")
    is_penalty = fields.Boolean("Is Surcharge?")
    is_active = fields.Boolean("Is Active?", default=True)
    parent_id = fields.Many2one('payment.type', "Payment")
    child_ids = fields.One2many('payment.type', 'parent_id', 'Components')
    domain = fields.Selection(
        [('New', 'New Students'),
         ('Programme', 'Programme'),
         ('Faculty', 'Faculty'),
         ('General', 'General')],
        string="Domain", help="Fee application")

           
class State(models.Model):
    _description = "State"
    _name = 'academic.state'
    _order = 'name'

    lga_ids = fields.One2many('state.lga', 'state_id', 'LGAs')
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=False)
    country_id = fields.Many2one('res.country', 'Country')


class StateLga(models.Model):
    _description = "LGA"
    _name = 'state.lga'
    _order = 'name'

    state_id = fields.Many2one('academic.state', 'State', required=True)
    name = fields.Char('Local Government Area', size=64, required=True)


class LegacyStudentResult(models.Model):
    """ Defining Template For Student Result Import"""
    _name = "academic.legacy.student.result"
    _description = "Legacy Student Result"
    _order = "matric asc"
    _rec_name = "course"

    session = fields.Char('Session', required=True)
    course = fields.Char('Course', required=True)
    level = fields.Char('Level', required=True)
    dept = fields.Char('Dept', required=True)
    semester = fields.Char('Semester', required=True)
    matric = fields.Char('Registration', required=True, index=1, help='matric')
    practicals = fields.Float('Practicals', required=False)
    exam = fields.Float('Exam', required=True)
    test = fields.Float('C/A', required=True)
    total = fields.Float(compute='_compute_total', string="Total", store=True, readonly=True)
    grade = fields.Char('Grade')
    status = fields.Selection(
        string='Status',
        selection=[('New', 'New'), ('Failed', 'Failed'), ('Processed', 'Processed')],
        default='New',
        readonly=True
    )
    remarks = fields.Char('Remarks')

    def _check_if_result_exist(self, student_id, course_id, session_id):
        domain = [('session_id', '=', session_id), ('student_id', '=', student_id), ('course_id', '=', course_id)]
        result = self.env['student.result.entry'].search_count(domain)
        return result > 0

    def partition(self, data):
        if " " in data:
            return data
        else:
            parts = re.split('(\d.*)', data)
            return "{} {}".format(parts[0], parts[1])

    def find(self, session, semester, course, matric):
        domain = [('session', '=', session), ('semester', '=', semester),
                  ('course', '=', course), ('matric', '=', matric)]
        return self.env['academic.legacy.student.result'].search(domain)

    @api.constrains('exam', 'test', 'practicals')
    def _check_total(self):
        for record in self:
            total = record.exam + record.test + record.practicals
            if total > 100.00:
                raise exceptions.ValidationError("'Total {}' is greater than 100".format(total))

    def delete(self, result):
        result.unlink()

    @api.depends('exam', 'test', 'practicals')
    def _compute_total(self):
        for record in self:
            record.total = record.exam + record.test + record.practicals

    @api.model
    def create(self, vals):
        # Sanitize data
        vals['session'] = str(vals["session"]).strip().replace(" ", "")
        vals['semester'] = str(vals["semester"]).strip().replace(" ", "").lower()
        vals['course'] = self.partition(str(vals["course"]).strip())
        vals['exam'] = float(str(vals["exam"]).strip())
        vals['test'] = float(str(vals["test"]).strip())
        vals['matric'] = str(vals["matric"]).replace(" ", "").strip()
        vals['dept'] = str(vals['dept']).upper().strip()

        # Remove Existing Record to create anew one.
        res = self.find(vals['session'], vals['semester'], vals['course'], vals['matric'])
        if res:
            self.delete(res)

        vals['level'] = str(vals["level"]).strip().replace(" ", "")

        return super(LegacyStudentResult, self).create(vals)

    def create_registration_record(self, student, session_id, level_id, semester_id):
        vals = {'programme_id': student.programme_id.id,
                'student_id': student.id,
                'session_id': session_id,
                'level_id': level_id,
                'is_legacy': True,
                'semester_id': semester_id}
        registration = self.env['student.registration'].create(vals)

        return registration

    def check_registration_record(self, student_id, session_id, semester_id):
        registration = self.env['student.registration'].search(
            [('session_id', '=', session_id), ('student_id', '=', student_id), ('semester_id', '=', semester_id)])
        return registration

    def update_result_record(self, student_id, course_id, session_id):
        domain = [('student_id', '=', student_id), ('session_id', '=', session_id),
                  ('course_id', '=', course_id)]
        result = self.env['student.result.entry'].search(domain)
        _logger.info("Executing update_result_record {} ".format(result))
        if result:
            _logger.info("Updating Result {}".format(result))
            vals = {'status': 'Approved', 'ca_score': self.exam, 'test_score': self.test,
                    'practicals_score': self.practicals}
            result.write(vals)
            _logger.info("Result updated to {}".format(result))

    def action_process(self):
        for record in self:
            if record.status == "Processed":
                return True
            else:
                try:
                    student = self.env['quickledger.student'].search([('matriculation_number', '=', record.matric)])
                    if not student:
                        raise ValueError("Student with the matric number {} was not found".format(record.matric))

                    session = self.env['academic.session'].search([('code', '=', record.session)])
                    if not session:
                        raise ValueError("Invalid Academic Session {}".format(record.session))

                    course = self.env['programme.course.entry'].search(
                        [('code', '=', record.course), ('programme_id', '=', student.programme_id.id)], limit=1)
                    if not course:
                        raise ValueError("{} was not found for {}".format(record.course, student.programme_id.name))

                    level = self.env['quickledger.level'].search(
                        ["|", ('code', '=', record.level), ('name', '=', record.level)])
                    if not level:
                        raise ValueError("Invalid Level {}".format(record.level))

                    semester = self.env['quickledger.semester'].search(
                        ["|", ('code', '=', record.semester), ('code', "=", record.semester.lower())])
                    if not semester:
                        raise ValueError("Invalid Semester code {}".format(record.semester))

                    # If already processed skip, handles duplicates
                    # if course and self._check_if_result_exist(student.id, course.id, session.id):
                    #    record.write({'status': 'Processed'})
                    #    return True

                    result_book = self.env['student.result'].search([('student_id', '=', student.id)])
                    registration = record.check_registration_record(student.id, session.id, semester.id)
                    registration = registration if registration else record.create_registration_record(student,
                                                                                                       session.id,
                                                                                                       level.id,
                                                                                                       semester.id)
                    registration.add_course_entry(course.id, False)
                    scores = {'exam': record.exam, 'practicals': record.practicals, 'test': record.test}
                    registration.add_student_result_entry(result_book, course.id, scores)
                    registration.action_recompute_cgpa()
                    result_book.action_recompute_cgpa()

                except ValueError as e:
                    return record.write({'status': 'Failed', 'remarks': e})

                except Exception as e:
                    return record.write({'status': 'Failed', 'remarks': e})

                return record.write({'status': 'Processed', 'remarks': 'Processed Successfully'})


class LegacyPayment(models.Model):
    """ Defining Template For Student Import"""
    _name = "legacy.payment"
    _description = "Legacy Payment"
    _order = "matric asc"

    name = fields.Char('NAME', required=False)
    payment_date = fields.Char('DATE', required=True)
    level = fields.Char('LEVEL', required=True)
    dept = fields.Char('DEPT', required=True)
    matric = fields.Char('MATRIC', required=True, index=1, help='matric')
    session = fields.Char('SESSION', required=True)
    account = fields.Char('ACCOUNT', required=False)
    receipt = fields.Char('RECEIPT', required=False)
    teller_number = fields.Char('TELLER', required=False)
    amount = fields.Char('AMOUNT', required=True)
    purpose = fields.Char('PURPOSE', required=True)
    status = fields.Selection(
        string='Status',
        selection=[('New', 'New'), ('Failed', 'Failed'), ('Processed', 'Processed')],
        default='New',
        readonly=True
    )
    remarks = fields.Char('Remarks')
    
    def _is_valid_date(self, date_text):
        try:
            if date_text != datetime.strptime(date_text, "%d/%m/%y").strftime("%d/%m/%y"):
                raise ValueError
            
            return True
        except ValueError:
            return False

    def _format_date(self, date):
        parts = str(date).split("/")
        day = "0" + parts[1] if len(parts[1]) == 1 else parts[1]
        month = "0" + parts[0] if len(parts[0]) == 1 else parts[0]
        year = parts[2]
        formatted_date = "{}-{}-{}".format(day, month, year)

        if len(year) == 4:
            # gets the last 2 digits
            year = parts[2][2:]
            formatted_date = "{}-{}-{}".format(day, month, year)
            if self._is_valid_date(formatted_date):
                return formatted_date
            else:
                return "{}-{}-{}".format(month, day, year)
        else:
            if self._is_valid_date(formatted_date):
                return formatted_date
            else:
                return "{}-{}-{}".format(month, day, year)
            

    @api.model
    def create(self, vals):
        vals['level'] = str(vals["level"]).strip().replace(" ", "")
        vals['name'] = str(vals["name"]).strip().title()
        vals['matric'] = str(vals["matric"]).replace(" ", "").strip()
        vals['dept'] = str(vals['dept']).upper().strip()
        vals['purpose'] = str(vals['purpose']).title().strip()
        vals['session'] = str(vals["session"]).strip().replace(" ", "")
        vals['payment_date'] = vals['payment_date'] # self._format_date(vals['payment_date'])

        return super(LegacyPayment, self).create(vals)

    def _create_payment_entry(self, student_id, session_id, level_id, transaction_details):
        vals = {}
        vals['student_id'] = student_id
        vals['session_id'] = session_id
        vals['level_id'] = level_id
        vals['payment_date'] = transaction_details['payment_date']
        vals['amount'] = transaction_details['amount']
        vals['fee_ids'] = [(6, 0, transaction_details['fee_ids'])]
        vals['ledger_id'] = self.env['student.ledger'].search([('student_id', '=', student_id)]).id

        if 'bank_id' in transaction_details:
            vals['bank_id'] = transaction_details['bank_id']
        if 'teller_number' in transaction_details:
            vals['teller_number'] = transaction_details['teller_number']
        
        return self.env['academic.payment.entry'].create(vals)
    

    def action_process(self):
        for record in self:
            if record.status == "Processed":
                return True
            else:
                try:
                    transaction_details = {
                        'amount': record.amount, 
                        'payment_date': record.payment_date
                        }
                    
                    processed_fees = []
                    
                    if not self._is_valid_date(record.payment_date):
                        raise ValueError(f"Invalid date format '{record.payment_date}' expected format is 2000-10-02")
                        
                    if record.account:
                        transaction_details['bank_id'] = self.env["res.partner.bank"].search(
                            [("acc_number", '=', record.account)])
                    if record.receipt:
                        transaction_details['receipt'] = record.receipt
                    if record.teller_number:
                        transaction_details['teller_number'] = record.teller_number
                    
                    dept = self.env['academic.department'].search(['|',
                                                                   ('previous_code', '=', record.dept),
                                                                   ('code', '=', record.dept)])
                    if not dept:
                        raise ValueError(f"Invalid Department Code {record.dept}")
                   
                    level = self.env['quickledger.level'].search(["|", ('code', '=', record.level),
                                                               ('name', '=', record.level)])
                    if not level:
                        raise ValueError("Invalid Level {}".format(record.level))
                         
                    diploma_id = level.diploma_id.id
                    semester = self.env["academic.semester"].search([("code", '=', '1st')])
                    session = self.env["academic.session"].search([("code", '=', record.session)])
                   
                    if not session:
                        raise ValueError("Invalid Session {}".format(record.session))
                   
                    student = self.env["student.student"].search([("matriculation_number", '=', record.matric)])
                    if not student:
                        raise ValueError("Student with Matric Number {} not found".format(record.matric))

                    registration = self.env['student.registration'].search([('semester_id', '=', semester.id),('student_id', '=', student.id),('session_id', '=', session.id)])
                    if not registration:
                        registration = self.env['student.registration'].create({
                            'student_id': student.id,
                            'level_id': level.id,
                            'programme_id': student.programme_id.id, 
                            'semester_id': semester.id,
                            'session_id': session.id })
                        
                    fees = str(record.purpose).lower().split(",")
                    purposes = [fee.strip() for fee in fees]
                    payment_amount = float(record.amount)
                    allFees = registration.fee_entry_ids
                    applicableFees = allFees.filtered(lambda fee: str(fee.type_id.name).lower() in purposes)  

                    if not applicableFees:
                        raise ValueError("Invalid Fee Name {}".format(record.purpose))
    
                    total_amount_due = sum([fee.balance for fee in applicableFees])
                    if payment_amount > total_amount_due:
                        raise ValueError(f"The Amount Paid {record.amount} is more than the amount due {total_amount_due}")

                    for fee in fees:
                        for applicableFee in applicableFees:
                            if payment_amount and applicableFee.balance >= payment_amount:
                                applicableFee.write({'amount_paid' : (applicableFee.amount_paid + payment_amount)})
                                payment_amount = 0.00
                                processed_fees.append(applicableFee.id)
                                break
                            elif payment_amount and applicableFee.balance < payment_amount:
                                payment_amount = payment_amount - applicableFee.balance
                                applicableFee.write({'amount_paid' : applicableFee.amount_due})
                                processed_fees.append(applicableFee.id)
                                break
                        else:
                            raise ValueError("Invalid Fee Name {}".format(fee))
                        
                    transaction_details['fee_ids'] = processed_fees
                    self._create_payment_entry(student.id, session.id, level.id, transaction_details)                        
                
                except ValueError as e:
                    record.write({'status': "Failed", 'remarks': e})
                    return False
                
                except Exception as e:
                    record.write({'status': "Failed", 'remarks': e})
                    return False
                
                record.write({'status': "Processed", 'remarks': "Successfully"})
                return True
        

class LegacyStudent(models.Model):
    """ Defining Template For Student Import"""
    _name = "academic.legacy.student"
    _description = "Legacy Student"
    _order = "matric asc"

    name = fields.Char('Name', size=128, required=True)
    matric = fields.Char('Registration. No', required=True, index=1, help='matric')
    application_number = fields.Char('Application. No', size=64, help='Application No.')
    phone = fields.Char('Phone Number', size=64)
    email = fields.Char('Email', size=32)
    level = fields.Char('Level', required=True)
    dept = fields.Char('Dept', required=True)
    status = fields.Selection(
        string='Status',
        selection=[('New', 'New'), ('Failed', 'Failed'), ('Processed', 'Processed')],
        default='New',
        readonly=True
    )
    remarks = fields.Char('Remarks')

    # NAU/2001/484557
    def _get_admission_year(self):
        parts = str(self.matric).split("/")
        if parts and len(parts) > 1:
            try:
                return int(parts[1])
            except Exception:
                raise ValueError("Invalid Registration Number {}".format(self.matric))
        else:
            raise ValueError("Invalid Registration Number {}".format(self.matric))

    def action_process(self):
        for record in self:
            if record.status == "Processed":
                return True
            else:
                try:
                    vals = {'matriculation_number': record.matric}
                    admission_year = self._get_admission_year()
                    admission_year_upper_bound = int(admission_year) + 1
                    code = str(admission_year) + "/" + str(admission_year_upper_bound)
                    session = self.env['academic.session'].search([('code', '=', code)])

                    if session:
                        vals['admission_year_id'] = session.id
                    else:
                        raise ValueError("Invalid Registration number {}".format(record.matric))
                    if record.phone:
                        vals['phone'] = "0" + record.phone

                    level = self.env['quickledger.level'].search([('code', '=', record.level)])
                    if not level:
                        raise ValueError("Invalid Level {}".format(record.level))

                    diploma_id = level.diploma_id.id
                    dept = self.env['quickledger.department'].search(
                        ['|', ('code', '=', record.dept), ('previous_code', '=', record.dept)])

                    if not dept:
                        raise ValueError("Invalid Department Code {}".format(record.dept))
                    programme = self.env['quickledger.programme'].search([('department_id', '=', dept.id),
                                                                          ('diploma_id', '=', diploma_id)])
                    
                    if not programme:
                        raise ValueError("Invalid Programme {} {} ".format(diploma_id.code, dept.name))

                    vals['level_id'] = level.id
                    vals['programme_id'] = programme.id

                    # Searches to see if the record already exists
                    student = self.env['quickledger.student'].search(
                        [('matriculation_number', '=', vals['matriculation_number'])])
                    if student:
                        self.write({'status': 'Processed', 'remarks': 'Processed Successfully'})
                        _logger.info("{} already exists".format(vals['matriculation_number']))
                        return True
                    else:
                        self.env['quickledger.student'].create(vals)

                except ValueError as v:
                    # _logger.info(v)
                    self.write({'status': 'Failed', 'remarks': v})
                    return False

                except Exception as e:
                    # _logger.info(e)
                    self.write({'status': 'Failed', 'remarks': e})
                    return False

                self.write({'status': 'Processed', 'remarks': 'Processed Successfully'})
                return True


class SchoolCourse(models.Model):
    """ Defining Template For Course Import"""
    _name = "academic.school.course"
    _description = "Course Import"
    _order = "title asc"
    _rec_name = "title"

    title = fields.Char('Title', required=True)
    code = fields.Char('Code', help='Code')
    units = fields.Char('Units', required=True, help='Units')
    semester = fields.Char('Semester', required=True)
    level = fields.Char('Level', required=True)
    department = fields.Char('Department', required=True)
    diploma = fields.Char('Degree', required=True)
    option = fields.Char('Option', required=False)
    status = fields.Selection(
        string='Status',
        selection=[('New', 'New'), ('Failed', 'Failed'), ('Processed', 'Processed')],
        default='New',
        readonly=True
    )
    remarks = fields.Char('Remarks')

    def partition(self, data):
        if " " in data:
            return data
        else:
            parts = re.split('(\d.*)', data)
            return "{} {}".format(parts[0], parts[1])

    def create_course_record(self, diploma_id, code, name, semester_id):
        vals = {'name': name, 'code': code, 'semester_id': semester_id, 'diploma_id': diploma_id}
        course = self.env['programme.course'].create(vals)
        return course

    def create_course_entry_record(self, course_id, units, programme_id, level_id, option):
        vals = {}
        if option:
            optionObj = self.env['quickledger.programme.option'].search(
                [('name', '=ilike', option), ('programme_id', '=', programme_id)])
            vals['option_id'] = optionObj.id

        vals['course_id'] = course_id
        vals['units'] = units
        vals['programme_id'] = programme_id
        vals['level_id'] = level_id
        course_entry = self.env['programme.course.entry'].create(vals)

        return course_entry

    def check_for_course_record(self, code):
        course = self.env['programme.course'].search([('code', '=', code)])
        return course

    def check_if_course_entry_exist(self, course_id, programme_id, option):
        domain = [('course_id', '=', course_id), ('programme_id', '=', programme_id)]
        if option:
            optionObj = self.env['quickledger.programme.option'].search(
                [('name', '=ilike', option), ('programme_id', '=', programme_id)])
            domain = [('course_id', '=', course_id), ('programme_id', '=', programme_id),
                      ('option_id', '=', optionObj.id)]

        course = self.env['programme.course.entry'].search_count(domain)
        return course > 0

    def action_process(self):
        for record in self:
            if record.status == "Processed":
                return True
            else:
                try:
                    departmentName = record.department
                    domainProgramme = []
                    diploma = self.env["quickledger.diploma"].search([("code", '=ilike', record.diploma)])
                    if not diploma:
                        raise ValueError("Invalid Degree '{}'".format(record.diploma))
                    
                    domainProgramme.append(('diploma_id', '=', diploma.id))

                    if str(record.department).find("CEP") or str(record.department).find("C.E.P"):
                        entry_status = self.env['quickledger.entry.status'].search([('name', '=', "CEP")])
                        domainProgramme.append(('entry_status_id', '=', entry_status.id))
                    
                    dept = self.env["quickledger.department"].search([("name", '=ilike', departmentName.strip(" CEP").strip())])
                    if not dept:
                        raise ValueError("Invalid Department '{}'".format(record.department))
                    domainProgramme.append(('department_id', '=', dept.id))
                    
                    programme = self.env['quickledger.programme'].search(domainProgramme)

                    if not programme:
                        raise ValueError("Invalid Programme {} {} ".format(diploma.code, dept.name))

                    level = self.env["quickledger.level"].search([("code", '=', record.level)])
                    if not level:
                        raise ValueError("Invalid Level {}".format(record.level))
                    semester = self.env["quickledger.semester"].search([("code", '=', record.semester)])
                    if not semester:
                        raise ValueError("Invalid Semester {}".format(record.semester))
                    diploma_id = programme.diploma_id.id
                    course = record.check_for_course_record(record.code)
                    if course:
                        course_entry = record.check_if_course_entry_exist(course.id, programme.id, record.option)
                        if not course_entry:
                            record.create_course_entry_record(course.id, record.units,
                                                              programme.id, level.id, record.option)
                        else:
                            raise ValueError("{} already exist for {}".format(course.code, programme.name))
                    else:
                        course = record.create_course_record(diploma_id, record.code, record.title, semester.id)
                        course_entry = record.check_if_course_entry_exist(course.id, programme.id, record.option)
                        if not course_entry:
                            record.create_course_entry_record(course.id, record.units, programme.id,
                                                              level.id, record.option)
                        else:
                            raise ValueError("{} already exist for {}".format(course.code, programme.name))
                except ValueError as e:
                    record.write({'status': "Failed", 'remarks': e})
                    return False
                except Exception as e:
                    record.write({'status': "Failed", 'remarks': e})
                    return False
                record.write({'status': "Processed", 'remarks': "Successfully"})
                return True

    @api.model
    def create(self, vals):
        vals['title'] = str(vals["title"]).strip().title()
        vals['code'] = self.partition(str(vals["code"]).strip().replace("  ", " "))
        vals['level'] = str(vals["level"]).strip().replace(" ", "")
        if vals['option']:
            vals['option'] = str(vals["option"]).strip()
        vals['diploma'] = str(vals["diploma"]).strip().replace("  ", " ")
        vals['department'] = str(vals["department"]).strip()

        return super(SchoolCourse, self).create(vals)


class AutoJobScheduler(models.Model):
    """ Defining Job Scheduler"""
    _name = "auto.job.scheduler"
    _description = "Automatic Job Scheduler"
    _order = "name asc"

    date = fields.Char('Date')
    name = fields.Char('Name', required=True)
    description = fields.Char('Description')

    @api.model
    def process_result(self):
        new_records = self.env['academic.legacy.student.result'].search([('status', '=', 'New')], limit=350)
        if new_records:
            for result in new_records:
                _logger.info(" Processing New Student ****** {} ******".format(result.matric))
                result.action_process()
        else:
            failed_records = self.env['academic.legacy.student.result'].search([('status', '=', 'Failed')], limit=350)
            for result in failed_records:
                _logger.info(" Processing Failed ****** {} ******".format(result.matric))
                result.action_process()

    @api.model
    def process_student(self):
        new_records = self.env['academic.legacy.student'].search([('status', '=', 'New')], limit=350)
        if new_records:
            for student in new_records:
                _logger.info(" Processing New ****** {} ******".format(student.name))
                student.action_process()
        else:
            failed_records = self.env['academic.legacy.student'].search([('status', '=', 'Failed')], limit=350)
            for student in failed_records:
                _logger.info(" Processing Failed ****** {} ******".format(student.name))
                student.action_process()

    @api.model
    def process_course(self):
        new_records = self.env['academic.school.course'].search([('status', '=', 'New')], limit=350)
        if new_records:
            for course in new_records:
                _logger.info(" Processing New ****** {} ******".format(course.code))
                course.action_process()
        else:
            failed_records = self.env['academic.school.course'].search([('status', '=', 'Failed')], limit=350)
            for course in failed_records:
                _logger.info(" Processing Failed ****** {} ******".format(course.code))
                course.action_process()
                

class Credentials(models.Model):
    """ Credentials """
    _name = "quickledger.credentials"
    _description = " Credentials"

    lecturer_id = fields.Many2one('quickledger.lecturer', 'Lecturer', required=True)
    institution = fields.Char('Institution', required=True, size=250)
    discipline = fields.Char('Discipline', required=True, size=250)
    remarks = fields.Text('Remarks')
    diploma_id = fields.Many2one('quickledger.diploma', 'Diploma', required=True)
    honour_id = fields.Many2one('quickledger.honour', 'Honour')
    exam_year = fields.Char(required=True, string='Year')
    
    def name_get(self):
        result = []
        for record in self:
            name = "{0} {1} ".format(record.diploma_id.code, record.discipline)
            result.append((record.id, name))
        return result
    
    
class Position(models.Model):
    """Position"""
    _name = "quickledger.position"
    _description = "Position"

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    entry_ids = fields.One2many('quickledger.position.entry', 'position_id', string='Entry')
    
    
class PositionEntry(models.Model):
    """Position"""
    _name = "quickledger.position.entry"
    _description = "Position Entry"
    
    @api.model
    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    entry_date = fields.Date('Date', required=True, default=_get_default_date)
    name = fields.Char(compute='_compute_name', string='Name', store=True)
    position_id = fields.Many2one('quickledger.position', string='Position', required=True)
    department_id = fields.Many2one('quickledger.department', string='Department', required=True)
    faculty_id = fields.Many2one(related='department_id.faculty_id', string='Faculty', readonly=True, store=True)
    lecturer_ids = fields.One2many('quickledger.lecturer', 'position_id', string='Lecturers')
    
    @api.depends('position_id', 'department_id')
    def _compute_name(self):
        for record in self:
            if record.position_id and record.department_id:
                record.name = "{} {}".format(record.position_id.name, record.department_id.name)

    
class Lecturer(models.Model):
    """ Defining Academic Staff"""
    _name = "quickledger.lecturer"
    _description = "Academic Staff"
    _order = "name asc"

    name = fields.Char('Name', required=True)
    surname = fields.Char('Surname', required=True)
    full_name = fields.Char(compute='_compute_full_name', string="Full Name", store=True)
    phone_number = fields.Char('Phone #', required=True)
    middle_name = fields.Char(string='Middle Name', required=False)
    marital_status = fields.Selection(
        selection=[('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced')],
        required=False,
        string='Marital Status')
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], required=True, string='Sex')
    address = fields.Text(string='Address', required=False)
    email = fields.Char('Email Address')
    title = fields.Selection(string="Title",
                             selection=[
                                 ('Dr', 'Dr'),
                                 ('Engr', 'Engr'),
                                 ('Mr', 'Mr'),
                                 ('Mrs', 'Mrs'),
                                 ('Prof', 'Prof')])
    department_id = fields.Many2one('quickledger.department', 'Department', required=True)
    credential_ids = fields.One2many('quickledger.credentials', 'lecturer_id', string='Credentials')
    course_ids = fields.Many2many(comodel_name='programme.course', string='Courses')
    faculty_id = fields.Many2one(related='department_id.faculty_id', string='Faculty', readonly=True, store=True)
    employment_date = fields.Date('Employment Date', required=False)
    middle_name = fields.Char(string='Middle Name', required=False)
    profile = fields.Text(string='Profile')
    marital_status = fields.Selection(
        selection=[('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced')],
        required=False,
        string='Marital Status')
    position_id = fields.Many2one('quickledger.position.entry', 'Position', required=False)
    image = fields.Binary(
        "Photograph", attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    
    @api.depends('name', 'surname', 'title')
    def _compute_full_name(self):
        for record in self:
            if record.title:
                record.full_name = "{0} {1} {2}".format(record.title, record.name, record.surname)
            else:
                record.full_name = "{0} {1}".format(record.name, record.surname)
    
    def name_get(self):
        result = []
        for record in self:
            name = "{0}".format(record.full_name)
            result.append((record.id, name))
        return result
    
    
class ResPartnerBank(models.Model):
    """Bank Accounts"""
    _name = "res.partner.bank"
    _inherit = "res.partner.bank"

    @api.depends('bank_id', 'acc_number')
    def _compute_bank_account_name(self):
        for record in self:
            record.name = f"{record.bank_id.name} ({record.acc_number})"

    
    @api.depends('bank_id', 'acc_number')
    def name_get(self):
        res = []
        for record in self:
            if record.bank_id.name:
                name = f"{record.bank_id.name} ({record.acc_number})"
                res.append((record.id, name))
        return res

    name = fields.Char(compute='_compute_bank_account_name', string="Account Name", store=True)

    
    

