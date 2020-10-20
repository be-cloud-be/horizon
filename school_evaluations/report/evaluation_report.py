# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 be-cloud.be
#                       Jerome Sonnet <jerome.sonnet@be-cloud.be>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
import time
import base64

from odoo import api, fields, models, tools, _
from odoo.exceptions import MissingError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class ReportEvaluationByTeacherWizard(models.TransientModel):
    _name = "school_evaluations.report_evaluation_by_teacher"
    _description = "Evaluations by Teacher Report"

    year_id = fields.Many2one('school.year', string='Year', default=lambda self: self.env.user.current_year_id, ondelete='cascade')
    teacher_id = fields.Many2one('res.partner', string='Teacher', ondelete='cascade', domain=[('teacher','=',True)])
    teacher_ids = fields.Many2many('res.partner', 'report_evaluation_by_teacher_teacher_rel', 'report_id', 'teacher_id', string='Teachers', ondelete='cascade', domain=[('teacher','=',True)])
    display_results = fields.Boolean(string='Display Current Results')
    freeze_first_session = fields.Boolean(string='Freeze First Session')
    message = fields.Text(string="Message")
    
    send_as_email = fields.Boolean(string="Send as email")
    
    @api.multi
    def print_report(self, data):
        self.ensure_one()
        data['year_id'] = self.year_id.id
        data['message'] = self.message
        data['display_results'] = self.display_results
        data['freeze_first_session'] = self.freeze_first_session
        if self.send_as_email :
            for teacher_id in self.teacher_ids:
                data['teacher_ids'] = [teacher_id.id]
                self.send_mail(teacher_id, data)
        else :
            if self.teacher_id:
                data['teacher_ids'] = [self.teacher_id.id] 
            elif self.teacher_ids:
                data['teacher_ids'] = self.teacher_ids.ids
            else:
                context = dict(self._context or {})
                data['teacher_ids'] = data.get('active_ids')
            return self.env['report'].get_action(self, 'school_evaluations.report_evaluation_by_teacher_content', data=data)
    
    
    def send_mail(self, teacher_id, data):
        """Generates a new mail message for the given template and record,
           and schedules it for delivery through the ``mail`` module's scheduler.
           :param int res_id: id of the record to render the template with
                              (model is taken from the template)
           :param bool force_send: if True, the generated mail.message is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
           :returns: id of the mail.message that was created
        """
        self.ensure_one()
        Mail = self.env['mail.mail']
        Attachment = self.env['ir.attachment']  # TDE FIXME: should remove dfeault_type from context
        
        template = self.env.ref('school_evaluations.mail_template_evaluation_email')
        for wizard_line in self:
            if template:
                
                # create a mail_mail based on values, without attachments
                values = template.generate_email(teacher_id.id)
                values['recipient_ids'] = [(6, 0, [teacher_id.id])]
                attachment_ids = values.pop('attachment_ids', [])
                attachments = values.pop('attachments', [])
                
                # add a protection against void email_from
                if 'email_from' in values and not values.get('email_from'):
                    values.pop('email_from')
                    
                mail = Mail.create(values)
        
                # manage attachments
                
                filename = "evaluations.pdf"
                
                report = self.env.ref('school_evaluations.report_evaluation_by_teacher')
                
                pdf_bin, _ = report.render_report([teacher_id.id], 'school_evaluations.report_evaluation_by_teacher_content', data=data)
                
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': base64.b64encode(pdf_bin),
                    'datas_fname': filename,
                    'res_model': 'res.partner',
                    'res_id': teacher_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                })
                
                # for attachment in attachments:
                #     attachment_data = {
                #         'name': attachment[0],
                #         'datas_fname': attachment[0],
                #         'datas': attachment[1],
                #         'type': 'binary',
                #         'res_model': 'mail.message',
                #         'res_id': mail.mail_message_id.id,
                #     }
                #     attachment_ids.append(Attachment.create(attachment_data).id)
                # if attachment_ids:
                #     values['attachment_ids'] = [(6, 0, attachment_ids)]
                
                mail.write({'attachment_ids': [(6, 0, [attachment.id])]})
        
                mail.send()
        
                return mail.id  # TDE CLEANME: return mail + api.returns ?

class ReportEvaluationByTeacher(models.AbstractModel):
    _name = 'report.school_evaluations.report_evaluation_by_teacher_content'
    
    @api.multi
    def render_html(self, data):
        res_data = []
        current_year_id = self.env.user.current_year_id
        if data['teacher_ids']:
            teacher_ids = self.env['res.partner'].browse(data['teacher_ids'])
        else:
            teacher_ids = self.env['school.individual_course_proxy'].search([['year_id', '=', data['year_id'] or current_year_id.id]]).mapped('teacher_id').sorted(key=lambda r: r.name)
        ids = []
        for teacher_id in teacher_ids:
            source_course_ids = self.env['school.individual_course_proxy'].search([['year_id', '=', data['year_id'] or current_year_id.id], ['teacher_id', '=', teacher_id.id]]).mapped('source_course_id').sorted(key=lambda r: r.name)
            courses = []
            for source_course_id in source_course_ids:
                individual_courses_ids = self.env['school.individual_course'].search([['year_id', '=', data['year_id'] or current_year_id.id], ['teacher_id', '=', teacher_id.id], ['source_course_id', '=', source_course_id.id]]).sorted(key=lambda r: r.student_id.name)
                courses.append({
                    'course':source_course_id,
                    'individual_courses':individual_courses_ids,
                })
            res_data.append({
                'teacher_id':teacher_id,
                'courses':courses,
                })
            ids.append(teacher_id.id)
        docargs = {
            'doc_ids': ids,
            'doc_model': self.env['res.partner'],
            'data': res_data,
            'time': time,
            'message': data['message'],
            'display_results':data['display_results'],
            'freeze_first_session':data['freeze_first_session'],
        }
        return self.env['report'].render('school_evaluations.report_evaluation_by_teacher_content', docargs)