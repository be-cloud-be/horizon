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

from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError

from openerp.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

class CourseGroup(models.Model):
    '''Course Group'''
    _inherit = 'school.course_group'
    
    ## If set a course with an evaluation < 10 will make this course group not acquiered.
    enable_exclusion_bool = fields.Boolean(string='Enable exclusion evaluation', default=False)
    
    @api.multi
    def valuate_course_group(self):
        self.ensure_one()
        program_id = self.env.context.get('program_id')
        _logger.info('Add cg %s to %s' % (self.id, program_id))
        if program_id :
            program_id = self.env['school.individual_program'].browse(program_id)[0]
            courses = []
            for course in self.course_ids:
                courses.append((0,0,{'source_course_id': course.id, 'dispense' : True}))
            cg = program_id.valuated_course_group_ids.create({
                'valuated_program_id' : program_id.id,
                'source_course_group_id': self.id, 
                'acquiered' : 'A',
                'course_ids': courses,
                'state' : 'candidate',})
            program_id._get_total_acquiered_credits()
            return {
                'value' : {
                    'total_acquiered_credits' : program_id.total_acquiered_credits,
                    'total_registered_credits' : program_id.total_registered_credits,
                    'valuated_course_group_ids' : (6, 0, program_id.valuated_course_group_ids.ids)
                },
            }
    
class IndividualProgram(models.Model):
    '''Individual Program'''
    _inherit='school.individual_program'
    
    state = fields.Selection([
            ('draft','Draft'),
            ('progress','In Progress'),
            ('awarded', 'Awarded'),
            ('abandonned', 'Abandonned'),
        ], string='Status', index=True, default='draft',copy=False,
        help=" * The 'Draft' status is used when results are not confirmed yet.\n"
             " * The 'In Progress' status is used during the cycle.\n"
             " * The 'Awarded' status is used when the cycle is awarded.\n"
             " * The 'Abandonned' status is used if a student leave the program.\n"
             ,track_visibility='onchange')
    
    abandonned_date = fields.Date('Abandonned Date')
    
    @api.multi
    def set_to_draft(self, context):
        # TODO use a workflow to make sure only valid changes are used.
        return self.write({'state': 'draft'})
    
    @api.multi
    def set_to_progress(self, context):
        # TODO use a workflow to make sure only valid changes are used.
        return self.write({'state': 'progress'})
    
    @api.multi
    def set_to_awarded(self, context, grade_year_id=None, grade=None, grade_comments=None):
        # TODO use a workflow to make sure only valid changes are used.
        if(grade):
            self.write({'state': 'awarded',
                           'grade' : grade,
                           'grade_year_id' : grade_year_id,
                           'grade_comments' : grade_comments,
                           'graduation_date' : fields.Date.today(),
            })
        else:
            self.write({'state': 'awarded',
                        'grade_year_id' : grade_year_id,
                        'graduation_date' : fields.Date.today(),
            })
        
    @api.multi
    def set_to_abandonned(self, context):
        # TODO use a workflow to make sure only valid changes are used.
        return self.write({'state': 'abandonned','abandonned_date':fields.Date.today()})
    
    historical_bloc_1_eval = fields.Float(string="Hist Bloc 1 Eval",track_visibility='onchange',digits=dp.get_precision('Evaluation'))
    historical_bloc_1_credits = fields.Integer(string="Hist Bloc 1 ECTS",track_visibility='onchange')
    
    historical_bloc_2_eval = fields.Float(string="Hist Bloc 2 Eval",track_visibility='onchange',digits=dp.get_precision('Evaluation'))
    historical_bloc_2_credits = fields.Integer(string="Hist Bloc 2 ECTS",track_visibility='onchange')
    
    grade = fields.Selection([
            ('without','Without Grade'),
            ('satisfaction','Satisfaction'),
            ('distinction','Distinction'),
            ('second_class', 'Second Class Honor'),
            ('first_class', 'First Class Honor'),
        ],string="Grade",track_visibility='onchange')
    
    grade_year_id = fields.Many2one('school.year', string="Graduation year",track_visibility='onchange')
    
    graduation_date = fields.Date(string="Graduation Date",track_visibility='onchange')
    
    grade_comments = fields.Text(string="Grade Comments",track_visibility='onchange')
    
    evaluation = fields.Float(string="Evaluation",compute="compute_evaluation",digits=dp.get_precision('Evaluation'))
    
    total_registered_credits = fields.Integer(compute='_get_total_acquiered_credits', string='Registered Credits',track_visibility='onchange')
    total_acquiered_credits = fields.Integer(compute='_get_total_acquiered_credits', string='Acquiered Credits', store=True, track_visibility='onchange')

    program_completed = fields.Boolean(compute='_get_total_acquiered_credits', string="Program Completed", store=True,track_visibility='onchange')

    valuated_course_group_ids = fields.One2many('school.individual_course_group', 'valuated_program_id', string='Valuated Courses Groups', track_visibility='onchange')

    @api.depends('valuated_course_group_ids', 'required_credits', 'bloc_ids.state','bloc_ids.total_acquiered_credits','historical_bloc_1_credits','historical_bloc_2_credits')
    @api.one
    def _get_total_acquiered_credits(self):
        _logger.debug('Trigger "_get_total_acquiered_credits" on Program %s' % self.name)
        total = sum(cg.total_credits for cg in self.valuated_course_group_ids) + sum(bloc_id.total_acquiered_credits if bloc_id.state in ['awarded_first_session','awarded_second_session','failed'] else 0 for bloc_id in self.bloc_ids) or 0
        total_current = sum(bloc_id.total_credits if bloc_id.state in ['progress','postponed'] else 0 for bloc_id in self.bloc_ids)
        self.total_acquiered_credits = total + self.historical_bloc_1_credits + self.historical_bloc_2_credits
        self.program_completed = self.required_credits > 0 and self.total_acquiered_credits >= self.required_credits
        self.total_registered_credits = self.total_acquiered_credits + total_current
        self.program_completed = self.required_credits > 0 and self.total_acquiered_credits >= self.required_credits
    
    @api.depends('valuated_course_group_ids')
    def _onchange_valuated_course_group_ids(self):
        for cg in self.valuated_course_group_ids :
            cg.course_ids.write({
                'dispense' : True
            })
            self._get_total_acquiered_credits()
            
    @api.depends('grade')
    def _onchange_grade(self):
        if self.grade:
            graduation_date = fields.Date.today()

    @api.depends('valuated_course_group_ids', 'bloc_ids.evaluation','historical_bloc_1_eval','historical_bloc_2_eval')
    @api.one
    def compute_evaluation(self):
        total = 0
        credit_count = 0
        for bloc in self.bloc_ids:
            if bloc.evaluation > 0 : # if all is granted do not count
                total += bloc.evaluation * bloc.total_credits
                credit_count += bloc.total_credits
        if self.historical_bloc_1_eval > 0:
            total += self.historical_bloc_1_eval * self.historical_bloc_1_credits
            credit_count += self.historical_bloc_1_credits
        if self.historical_bloc_2_eval > 0:
            total += self.historical_bloc_2_eval * self.historical_bloc_2_credits
            credit_count += self.historical_bloc_2_credits
        if credit_count > 0:
            self.evaluation = total/credit_count
        
    @api.depends('valuated_course_group_ids', 'bloc_ids.evaluation','historical_bloc_1_eval','historical_bloc_2_eval')
    @api.multi
    def compute_evaluation_details(self):
        self.ensure_one();
        ret = [0,0,0,0,0,0]
        if self.historical_bloc_1_eval > 0:
            ret[0] = self.historical_bloc_1_eval
        if self.historical_bloc_2_eval > 0:
            ret[1] = self.historical_bloc_2_eval
        for bloc in self.bloc_ids:
            ret[int(bloc.source_bloc_level)-1] = bloc.evaluation
        return {
            'bloc_evaluations' : ret
        }
    
    not_acquired_ind_course_group_ids = fields.One2many('school.individual_course_group', string='Not Acquiered Courses Groups',compute='_compute_ind_course_group_ids_eval')
    acquired_ind_course_group_ids = fields.One2many('school.individual_course_group', string='Acquiered Courses Groups',compute='_compute_ind_course_group_ids_eval')
    remaining_course_group_ids  = fields.One2many('school.course_group', string='Remaining Courses Groups',compute='_compute_ind_course_group_ids_eval')
    remaining_not_planned_course_group_ids  = fields.One2many('school.course_group', string='Remaining and Not Planned Courses Groups',compute='_compute_ind_course_group_ids_eval')
    
    @api.one
    def _compute_ind_course_group_ids_eval(self):
        self.not_acquired_ind_course_group_ids = self.ind_course_group_ids.filtered(lambda ic: ic.acquiered == 'NA')
        self.acquired_ind_course_group_ids = self.ind_course_group_ids.filtered(lambda ic: ic.acquiered == 'A') + self.valuated_course_group_ids
        self.remaining_course_group_ids = self.source_program_id.course_group_ids - self.acquired_ind_course_group_ids.mapped('source_course_group_id')
        if len(self.bloc_ids) > 0 :
            self.remaining_not_planned_course_group_ids = self.remaining_course_group_ids - self.bloc_ids[-1].course_group_ids.mapped('source_course_group_id')
        else :
            self.remaining_not_planned_course_group_ids = self.remaining_course_group_ids
    
class IndividualBloc(models.Model):
    '''Individual Bloc'''
    _inherit = 'school.individual_bloc'

    state = fields.Selection([
            ('draft','Draft'),
            ('progress','In Progress'),
            ('postponed', 'Postponed'),
            ('awarded_first_session', 'Awarded in First Session'),
            ('awarded_second_session', 'Awarded in Second Session'),
            ('failed', 'Failed'),
            ('abandoned','Abandoned'),
        ], string='Status', index=True, default='draft',
        copy=False,
        help=" * The 'Draft' status is used when results are not confirmed yet.\n"
             " * The 'In Progress' status is used during the courses.\n"
             " * The 'Postponed' status is used when a second session is required.\n"
             " * The 'Awarded' status is used when the bloc is awarded in either first or second session.\n"
             " * The 'Failed' status is used when the bloc is definitively considered as failed.\n"
             " * The 'Abandoned' status is when the student abandoned his bloc.\n"
             ,track_visibility='onchange')
    
    total_acquiered_credits = fields.Integer(compute="compute_credits",string="Acquiered Credits",store=True)
    total_acquiered_hours = fields.Integer(compute="compute_credits",string="Acquiered Hours",store=True)
    total_not_acquiered_credits = fields.Integer(compute='compute_credits', string='Not Acquiered Credits',store=True)
    total_not_acquiered_hours = fields.Integer(compute='compute_credits', string='Not Acquiered Hours',store=True)
    total_dispensed_credits = fields.Integer(compute="compute_credits",string="Dispensed Credits",store=True)
    total_dispensed_hours = fields.Integer(compute="compute_credits",string="Dispensed Hours",store=True)
    total_not_dispensed_credits = fields.Integer(compute="compute_credits",string="Not Dispensed Credits",store=True)
    total_not_dispensed_hours = fields.Integer(compute='compute_credits', string='Not Dispensed Hours',store=True)
    total_acquiered_not_dispensed_credits = fields.Integer(compute="compute_credits",string="Acquiered Not Dispensed Credits",store=True)
    
    evaluation = fields.Float(string="Evaluation",compute="compute_evaluation",digits=dp.get_precision('Evaluation'))
    decision = fields.Text(string="Decision",track_visibility='onchange')
    exclude_from_deliberation = fields.Boolean(string='Exclude from Deliberation', default=False)
    
    first_session_result = fields.Float(string="Evaluation",compute="compute_evaluation",digits=dp.get_precision('Evaluation'))
    second_session_result = fields.Float(string="Evaluation",compute="compute_evaluation",digits=dp.get_precision('Evaluation'))
    
    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'draft' :
            self.course_group_ids.write({'state': 'draft'})
        elif self.state == 'progress' :
            self.course_group_ids.write({'state': 'progress'})
        else :
            self.course_group_ids.write({'state': 'confirmed'})
    
    @api.multi
    def set_to_draft(self, context):
        # TODO use a workflow to make sure only valid changes are used.
        self.course_group_ids.write({'state': 'draft'})
        return self.write({'state': 'draft'})
    
    @api.multi
    def set_to_progress(self, context):
        self.course_group_ids.write({'state': 'progress'})
        # TODO use a workflow to make sure only valid changes are used.
        return self.write({'state': 'progress'})
    
    @api.multi
    def set_to_postponed(self, decision=None, context=None):
        # TODO use a workflow to make sure only valid changes are used.
        if isinstance(decision, dict):
            context = decision
            decision = None
        return self.write({'state': 'postponed','decision' : decision})
    
    @api.multi
    def set_to_awarded_first_session(self, decision=None, context=None):
        # TODO use a workflow to make sure only valid changes are used.
        if isinstance(decision, dict):
            context = decision
            decision = None
        self.course_group_ids.write({'state': 'confirmed'})
        return self.write({'state': 'awarded_first_session','decision' : decision})
        
    @api.multi
    def set_to_awarded_second_session(self, decision=None, context=None):
        # TODO use a workflow to make sure only valid changes are used.
        if isinstance(decision, dict):
            context = decision
            decision = None
        self.course_group_ids.write({'state': 'confirmed'})
        return self.write({'state': 'awarded_second_session','decision' : decision})
    
    @api.multi
    def set_to_failed(self, decision=None, context=None):
        # TODO use a workflow to make sure only valid changes are used.
        if isinstance(decision, dict):
            context = decision
            decision = None
        self.course_group_ids.write({'state': 'confirmed'})
        return self.write({'state': 'failed','decision' : decision})
    
    @api.multi
    def set_to_abandoned(self, decision=None, context=None):
        return self.write({'state': 'abandoned','decision' : None})
        
    @api.multi
    def report_send(self):
        """ Open a window to compose an email, with the default template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('school_evaluations.email_template_success_certificate', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='school.individual_bloc',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        
    @api.depends('course_group_ids.total_credits','course_group_ids.total_hours','course_group_ids.acquiered','course_group_ids.dispense', 'course_group_ids.first_session_computed_result_bool', 'course_group_ids.is_ghost_cg')
    @api.one
    def compute_credits(self):
        self.total_acquiered_credits = sum([icg.total_credits for icg in self.course_group_ids if icg.acquiered == 'A' and not icg.is_ghost_cg])
        self.total_acquiered_hours = sum([icg.total_hours for icg in self.course_group_ids if icg.acquiered == 'A' and not icg.is_ghost_cg])
        self.total_not_acquiered_credits = self.total_credits - self.total_acquiered_credits
        self.total_not_acquiered_hours = self.total_hours - self.total_acquiered_hours
        
        # WAS BEFORE May 2018
        #self.total_dispensed_credits = sum([icg.total_dispensed_credits for icg in self.course_group_ids])
        #self.total_dispensed_hours = sum([icg.total_dispensed_hours for icg in self.course_group_ids])
        
        self.total_dispensed_credits = sum([icg.total_credits for icg in self.course_group_ids if icg.dispense and not icg.is_ghost_cg])
        self.total_dispensed_hours = sum([icg.total_hours for icg in self.course_group_ids if icg.dispense and not icg.is_ghost_cg])
        self.total_not_dispensed_credits = self.total_credits - self.total_dispensed_credits
        self.total_not_dispensed_hours = self.total_hours - self.total_dispensed_hours
        self.total_acquiered_not_dispensed_credits = self.total_acquiered_credits - self.total_dispensed_credits
        
    @api.depends('course_group_ids.final_result','course_group_ids.total_weight','course_group_ids.acquiered', 'course_group_ids.is_ghost_cg')
    @api.one
    def compute_evaluation(self):
        total = 0
        total_first = 0
        total_second = 0
        total_weight = 0
        for icg in self.course_group_ids:
            if icg.acquiered == 'A' and icg.total_weight > 0 and not icg.is_ghost_cg : # if total_weight == 0 means full dispense
                total += icg.final_result * icg.total_weight
                total_first += icg.first_session_result * icg.total_weight
                total_second += icg.second_session_result * icg.total_weight
                total_weight += icg.total_weight
        if total_weight > 0 :
            self.evaluation = total / total_weight
            self.first_session_result = total_first / total_weight
            self.second_session_result = total_second / total_weight
        else:
            _logger.debug('total_weight is 0 on Bloc %s' % self.name)
            self.evaluation = None
        
    
class IndividualCourseGroup(models.Model):
    '''Individual Course Group'''
    _inherit = 'school.individual_course_group'
    
    valuated_program_id = fields.Many2one('school.individual_program', string="Program", ondelete='cascade', readonly=True)
    
    @api.constrains('bloc_id','valuated_program_id')
    def _check_bloc_id_constrains(self):
        if self.bloc_id and self.valuated_program_id :
            raise UserError('A Course Group cannot be valuated in a program and in a bloc at the same time.')
    
    @api.multi
    def valuate_course_group(self):
        self.ensure_one()
        program_id = self.bloc_id.program_id
        _logger.info('Add cg %s to %s' % (self.id, program_id))
        if program_id :
            self.course_ids.write({'dispense' : True})
            self.write({
                'bloc_id' : False,
                'valuated_program_id' : program_id.id,
                'acquiered' : 'A',
                'state' : 'candidate',})
            program_id._get_total_acquiered_credits()
            return {
                'value' : {
                    'total_acquiered_credits' : program_id.total_acquiered_credits,
                    'total_registered_credits' : program_id.total_registered_credits,
                    'valuated_course_group_ids' : (6, 0, program_id.valuated_course_group_ids.ids)
                },
            }
            
    ## Compute dispensed hours and ECTS
    
    total_dispensed_credits = fields.Integer(compute="compute_credits",string="Dispensed Credits",store=True)
    total_dispensed_hours = fields.Integer(compute="compute_credits",string="Dispensed Hours",store=True)
    total_not_dispensed_credits = fields.Integer(compute="compute_credits",string="Not Dispensed Credits",store=True)
    total_not_dispensed_hours = fields.Integer(compute='compute_credits', string='Not Dispensed Hours',store=True)
    
    @api.depends('course_ids.dispense')
    @api.one
    def compute_credits(self):
        self.total_dispensed_credits = sum([ic.credits for ic in self.course_ids if ic.dispense])
        self.total_dispensed_hours = sum([ic.hours for ic in self.course_ids if ic.dispense])
        self.total_not_dispensed_credits = self.total_credits - self.total_dispensed_credits
        self.total_not_dispensed_hours = self.total_hours - self.total_dispensed_hours
        
    # Actions
    @api.one
    def set_deliberated_to_ten(self, session = 1, message=''):
        if session == 1:
            self.write({
                'first_session_deliberated_result' : max(self.first_session_computed_result, 10),
                'first_session_deliberated_result_bool' : True,
                'first_session_note': message,
                'state' : 'finish',
            })
        else:
            self.write({
                'second_session_deliberated_result' : max(self.second_session_computed_result, 10) if self.second_session_computed_result_bool else max(self.first_session_computed_result, 10),
                'second_session_deliberated_result_bool' : True,
                'second_session_note': message,
                'state' : 'finish',
            })
    
    state = fields.Selection([
            ('draft','Draft'),
            ('progress','In Progress'),
            ('candidate','Candidate'),
            ('confirmed', 'Confirmed'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange',
        copy=False,
        help=" * The 'Draft' status is used when course group is only plan.\n"
             " * The 'In Progress' status is used when results are not confirmed yet.\n"
             " * The 'Candidate' status is used when the course group is candidate for valuation.\n"
             " * The 'Confirmed' status is when restults are confirmed.")
        
    @api.multi
    def set_to_confirmed(self, context):
        return self.write({'state': 'confirmed'})
    
    ## If set a course with an evaluation < 10 will make this course group not acquiered.
    
    enable_exclusion_bool = fields.Boolean(string='Enable exclusion evaluation', related="source_course_group_id.enable_exclusion_bool", readonly=True)
    
    ## First Session ##
    
    first_session_computed_result = fields.Float(compute='compute_average_results', string='First Session Computed Result', store=True, digits=dp.get_precision('Evaluation'))
    first_session_computed_result_bool= fields.Boolean(compute='compute_average_results', string='First Session Computed Active', store=True)
    first_session_computed_exclusion_result_bool= fields.Boolean(compute='compute_average_results', string='First Session Exclusion Result', store=True)
    
    first_session_deliberated_result = fields.Char(string='First Session Deliberated Result',track_visibility='onchange')
    first_session_deliberated_result_bool= fields.Boolean(string='First Session Deliberated Active',track_visibility='onchange')
    
    first_session_result= fields.Float(compute='compute_first_session_results', string='First Session Result', store=True, digits=dp.get_precision('Evaluation'))
    first_session_result_bool= fields.Boolean(compute='compute_first_session_results', string='First Session Active', store=True)
    first_session_acquiered = fields.Selection(([('A', 'Acquired'),('NA', 'Not Acquired')]), compute='compute_first_session_acquiered', string='First Session Acquired Credits',default='NA',store=True,required=True,track_visibility='onchange')
    first_session_note = fields.Text(string='First Session Notes')
    
    ## Second Session ##
    
    second_session_computed_result = fields.Float(compute='compute_average_results', string='Second Session Computed Result', store=True,digits=dp.get_precision('Evaluation'))
    second_session_computed_result_bool= fields.Boolean(compute='compute_average_results', string='Second Session Computed Active', store=True)
    second_session_computed_exclusion_result_bool= fields.Boolean(compute='compute_average_results', string='Second Session Exclusion Result', store=True)
    
    second_session_deliberated_result = fields.Char(string='Second Session Deliberated Result', digits=(5, 2),track_visibility='onchange')
    second_session_deliberated_result_bool= fields.Boolean(string='Second Session Deliberated Active',track_visibility='onchange')
    
    second_session_result= fields.Float(compute='compute_second_session_results', string='Second Session Result', store=True,digits=dp.get_precision('Evaluation'))
    second_session_result_bool= fields.Boolean(compute='compute_second_session_results', string='Second Session Active', store=True)
    second_session_acquiered = fields.Selection(([('A', 'Acquired'),('NA', 'Not Acquired')]), compute='compute_second_session_acquiered',string='Second Session Acquired Credits',default='NA',store=True,required=True,track_visibility='onchange')
    second_session_note = fields.Text(string='Second Session Notes')
    
    ## Final ##
    
    dispense =  fields.Boolean(compute='compute_dispense', string='Valuation',default=False,track_visibility='onchange', store=True)
    
    final_result = fields.Float(compute='compute_final_results', string='Final Result', store=True,digits=dp.get_precision('Evaluation'),track_visibility='onchange')
    final_result_disp = fields.Char(string='Final Result Display', compute='compute_results_disp')
    final_result_bool = fields.Boolean(compute='compute_final_results', string='Final Active')
    
    acquiered = fields.Selection(([('A', 'Acquiered'),('NA', 'Not Acquiered')]), compute='compute_acquiered', string='Acquired Credits', store=True, track_visibility='onchange',default='NA')
    
    final_note = fields.Text(string='Final Notes')
    
    @api.one
    def compute_results_disp(self):
        if not self.final_result_bool:
            self.final_result_disp = ""
        if self.dispense:
            self.final_result_disp = "Val"
        else :
            self.final_result_disp = "%.2f" % self.final_result
    
    def _parse_result(self,input):
        f = float(input)
        if(f < 0 or f > 20):
            raise ValidationError("Evaluation shall be between 0 and 20")
        else:
            return f
    
    ## override so that courses with dispense and no deferred results are excluded from computation
    @api.depends('course_ids.hours','course_ids.credits','course_ids.c_weight')
    @api.one
    def _get_courses_total(self):
        _logger.debug('Trigger "_get_courses_total" on Course Group %s' % self.name)
        self.total_hours = sum(course.hours for course in self.course_ids)
        self.total_credits = sum(course.credits for course in self.course_ids)
        self.total_weight = sum(course.c_weight for course in self.course_ids)

    @api.depends('course_ids.first_session_result_bool','course_ids.first_session_result','course_ids.second_session_result_bool','course_ids.second_session_result','course_ids.c_weight','course_ids.weight')
    @api.one
    def compute_average_results(self):
        _logger.debug('Trigger "compute_average_results" on Course Group %s' % self.name)
        ## Compute Weighted Average
        running_first_session_result = 0
        running_second_session_result = 0
        self.first_session_computed_result_bool = False
        self.first_session_computed_exclusion_result_bool = False
        self.second_session_computed_result_bool = False
        self.second_session_computed_exclusion_result_bool = False
        
        for ic in self.course_ids:
            # Compute First Session 
            if ic.first_session_result_bool :
                running_first_session_result += ic.first_session_result * ic.c_weight
                self.first_session_computed_result_bool = True
                if ic.first_session_result < 10 :
                    self.first_session_computed_exclusion_result_bool = True
            # Compute Second Session
            if ic.second_session_result_bool :
                running_second_session_result += ic.second_session_result * ic.c_weight
                self.second_session_computed_result_bool = True
                if max(ic.first_session_result,ic.second_session_result) < 10 :
                    self.second_session_computed_exclusion_result_bool = True
                
        if self.first_session_computed_result_bool :
            if self.total_weight > 0:
                self.first_session_computed_result = running_first_session_result / self.total_weight
        if self.second_session_computed_result_bool :
            if self.total_weight > 0:
                self.second_session_computed_result = running_second_session_result / self.total_weight
    
    @api.depends('first_session_deliberated_result_bool','first_session_deliberated_result','first_session_computed_result_bool','first_session_computed_result')
    @api.one
    def compute_first_session_results(self):
        _logger.debug('Trigger "compute_first_session_results" on Course Group %s' % self.name)
        ## Compute Session Results
        if self.first_session_deliberated_result_bool :
            try:
                f = self._parse_result(self.first_session_deliberated_result)
            except ValueError:
                self.write('first_session_deliberated_result', None)
                raise UserError(_('Cannot decode %s, please encode a Float eg "12.00".' % self.first_session_deliberated_result))
            #if (f < self.first_session_computed_result):
            #    # TODO : take care of this - removed due to Cours artistiques B - Art dramatique - 2 - 2015-2016 - VALERIO Maddy 
            #    # raise ValidationError("Deliberated result must be above computed result, i.e. %s > %s." % (self.first_session_deliberated_result, self.first_session_computed_result))
            self.first_session_result = f
            #else:
            #    self.first_session_result = f
            self.first_session_result_bool = True
        elif self.first_session_computed_result_bool :
            self.first_session_result = self.first_session_computed_result
            self.first_session_result_bool = True
        else :
            self.first_session_result = 0
            self.first_session_result_bool = False
    
    @api.depends('first_session_result_bool','first_session_result','first_session_computed_exclusion_result_bool')
    @api.one
    def compute_first_session_acquiered(self):
        _logger.debug('Trigger "compute_first_session_acquiered" on Course Group %s' % self.name)
        self.first_session_acquiered = 'NA'
        #if self.first_session_deliberated_result_bool:
        #    self.first_session_acquiered = 'A'
        #el
        if self.enable_exclusion_bool :
            if self.first_session_result >= 10 and (not self.first_session_computed_exclusion_result_bool or self.first_session_deliberated_result_bool):
                self.first_session_acquiered = 'A'
        else:
            if self.first_session_result >= 10 : # cfr appel Ingisi 27-06 and (not self.first_session_computed_exclusion_result_bool or self.first_session_deliberated_result_bool):
                self.first_session_acquiered = 'A'

    @api.depends('second_session_deliberated_result_bool','second_session_deliberated_result','second_session_computed_result_bool','second_session_computed_result')
    @api.one
    def compute_second_session_results(self):
        _logger.debug('Trigger "compute_second_session_results" on Course Group %s' % self.name)
        if self.second_session_deliberated_result_bool :
            try:
                f = self._parse_result(self.second_session_deliberated_result)
            except ValueError:
                self.write('second_session_deliberated_result', None)
                raise UserError(_('Cannot decode %s, please encode a Float eg "12.00".' % self.second_session_deliberated_result))
            if (f < self.second_session_computed_result):
                raise ValidationError("Deliberated result must be above computed result, i.e. %s > %s." % (self.second_session_deliberated_result, self.second_session_computed_result))
            else:
                self.second_session_result = f
            self.second_session_result_bool = True
        elif self.second_session_computed_result_bool :
            self.second_session_result = self.second_session_computed_result
            self.second_session_result_bool = True
        else :
            self.second_session_result = 0
            self.second_session_result_bool = False

    @api.depends('second_session_result_bool','second_session_result','first_session_acquiered')
    @api.one
    def compute_second_session_acquiered(self):
        _logger.debug('Trigger "compute_second_session_acquiered" on Course Group %s' % self.name)
        self.second_session_acquiered = self.first_session_acquiered
        if self.second_session_deliberated_result_bool:
            self.second_session_acquiered = 'A'
        elif self.enable_exclusion_bool :
            if self.second_session_result >= 10 and (not self.second_session_computed_exclusion_result_bool or self.second_session_deliberated_result_bool):
                self.second_session_acquiered = 'A'
        else:    
            if self.second_session_result >= 10 : # and (not self.second_session_computed_exclusion_result_bool or self.second_session_deliberated_result_bool):
                self.second_session_acquiered = 'A'

    @api.depends('first_session_result',
                 'first_session_result_bool',
                 'first_session_acquiered',
                 'second_session_result',
                 'second_session_result_bool',
                 'second_session_acquiered')
    @api.one
    def compute_final_results(self):
        _logger.debug('Trigger "compute_final_results" on Course Group %s' % self.name)
        ## Compute Final Results
        if self.second_session_result_bool :
            self.final_result = self.second_session_result
            self.final_result_bool = True
        elif self.first_session_result_bool :
            self.final_result = self.first_session_result
            self.final_result_bool = True
        else :
            self.final_result_bool = False

    @api.depends('course_ids.dispense')
    @api.one
    def compute_dispense(self):
        # Check if Course Group is dispensed
        all_dispensed = True
        for ic in self.course_ids:
            all_dispensed = all_dispensed and ic.dispense
        if all_dispensed :
            self.dispense = True
            self.acquiered  = 'A'

    @api.depends('dispense',
                 'second_session_acquiered')
    @api.one
    def compute_acquiered(self):
        if self.dispense:
            self.acquiered  = 'A'
        else :
            self.acquiered = self.second_session_acquiered
    
class Course(models.Model):
    '''Course'''
    _inherit = 'school.course'
    
    type = fields.Selection(([('S', 'Simple'),('C', 'Complex')]), string='Type', default="S")

class IndividualCourse(models.Model):
    '''Individual Course'''
    _inherit = 'school.individual_course'
    
    ## Type and weight for average computation (ie 0 for dispenses) ##
    
    type = fields.Selection(([('S', 'Simple'),('C', 'Complex'),('D','Deferred')]),compute='compute_type', string='Type', store=True, default="S")
    c_weight =  fields.Float(compute='compute_weight', readonly=True, store=True)

    ## Evaluation ##
    
    ann_result= fields.Char(string='Annual Result',track_visibility='onchange')
    jan_result= fields.Char(string='January Result',track_visibility='onchange')
    jun_result= fields.Char(string='June Result',track_visibility='onchange')
    sept_result= fields.Char(string='September Result',track_visibility='onchange')
    
    ## First Session ##
    
    first_session_result= fields.Float(compute='compute_results', string='First Session Result', store=True, group_operator='avg',digits=dp.get_precision('Evaluation'))
    first_session_result_bool = fields.Boolean(compute='compute_results', string='First Session Active', store=True)
    first_session_note = fields.Text(string='First Session Notes')
    
    first_session_result_disp = fields.Char(string='Final Result Display', compute='compute_first_session_result_disp')

    @api.one
    def compute_first_session_result_disp(self):
        if not self.first_session_result_bool:
            self.first_session_result_disp = ""
        if self.dispense:
            self.first_session_result_disp = "Disp"
        else :
            self.first_session_result_disp = "%.2f" % self.first_session_result
    
    ## Second Session ##
    
    second_session_result= fields.Float(compute='compute_results', string='Second Session Result', store=True, group_operator='avg',digits=dp.get_precision('Evaluation'))
    second_session_result_bool = fields.Boolean(compute='compute_results', string='Second Session Active', store=True)
    second_session_note = fields.Text(string='Second Session Notes')

    second_session_result_disp = fields.Char(string='Final Result Display', compute='compute_second_session_result_disp')

    @api.one
    def compute_second_session_result_disp(self):
        if not self.second_session_result_bool:
            self.second_session_result_disp = ""
        if self.dispense:
            self.second_session_result_disp = "Disp"
        else :
            self.second_session_result_disp = "%.2f" % self.second_session_result

    @api.model
    def create(self, values):
        if not(values.get('type', False)) and values.get('source_course_id', False):
            course = self.env['school.course'].browse(values['source_course_id'])
            values['type'] = course.type or 'S'
        result = super(IndividualCourse, self).create(values)
        return result
    
    @api.one
    @api.depends('dispense','weight','jun_result')
    def compute_weight(self):
        _logger.debug('Trigger "compute_weight" on Course %s' % self.name)
        if self.dispense and not self.jun_result:
            self.c_weight = 0
        else:
            self.c_weight = self.weight
    
    @api.one
    @api.depends('dispense', 'source_course_id.type')
    def compute_type(self):
        _logger.debug('Trigger "compute_type" on Course %s' % self.name)
        if self.dispense :
            self.type = 'D'
        else:
            self.type = self.source_course_id.type
            
    def _parse_result(self,input):
        f = float(input)
        if(f < 0 or f > 20):
            raise ValidationError("Evaluation shall be between 0 and 20")
        else:
            return f
    
    @api.depends('type','ann_result','jan_result','jun_result','sept_result')
    @api.one
    def compute_results(self):
        _logger.debug('Trigger "compute_results" on Course %s' % self.name)
        self.first_session_result_bool = False
        self.second_session_result_bool = False
        if self.type == 'D' :
            if self.jun_result :
                try:
                    f = self._parse_result(self.jun_result)
                    self.first_session_result = f
                    self.first_session_result_bool = True
                except ValueError:
                    self.first_session_result = 0
                    self.first_session_result_bool = False
                    raise UserError(_('Cannot decode %s in June Result, please encode a Float eg "12.00".' % self.jun_result))
                    
        if self.type in ['S','D']:
            f = -1
            if self.jan_result :
                try:
                    f = self._parse_result(self.jan_result)
                except ValueError:
                    self.first_session_result = 0
                    self.first_session_result_bool = False
                    raise UserError(_('Cannot decode %s in January Result, please encode a Float eg "12.00".' % self.jan_result))
            if self.jun_result :
                try:
                    f = self._parse_result(self.jun_result)
                except ValueError:
                    self.first_session_result = 0
                    self.first_session_result_bool = False
                    raise UserError(_('Cannot decode %s in June Result, please encode a Float eg "12.00".' % self.jun_result))
            if f >= 0 :
                self.first_session_result = f
                self.first_session_result_bool = True
            if self.sept_result :
                try:
                    f = self._parse_result(self.sept_result)
                    self.second_session_result = f
                    self.second_session_result_bool = True 
                except ValueError:
                    self.second_session_result = 0
                    self.second_session_result_bool = False
                    raise UserError(_('Cannot decode %s in September Result, please encode a Float eg "12.00".' % self.sept_result))
        if self.type in ['C']:
            ann = None
            jan = None
            if self.ann_result :
                try:
                    ann = self._parse_result(self.ann_result)
                except ValueError:
                    raise UserError(_('Cannot decode %s in January Result, please encode a Float eg "12.00".' % self.ann_result))
            if self.jan_result :
                try:
                    jan = self._parse_result(self.jan_result)
                except ValueError:
                    raise UserError(_('Cannot decode %s in January Result, please encode a Float eg "12.00".' % self.jan_result))
            if self.jun_result :
                try:
                    jun = self._parse_result(self.jun_result)
                    if self.ann_result and self.jan_result :
                        self.first_session_result = ann * 0.5 + (jan * 0.5 + jun * 0.5) * 0.5
                        self.first_session_result_bool = True
                    elif self.ann_result :
                        self.first_session_result = ann * 0.5 + jun * 0.5
                        self.first_session_result_bool = True
                    else:
                        self.first_session_result = 0
                        self.first_session_result_bool = False
                except ValueError:
                    self.first_session_result = 0
                    self.first_session_result_bool = False
                    raise UserError(_('Cannot decode %s in June Result, please encode a Float eg "12.00".' % self.jun_result))
            if self.sept_result :
                try:
                    sept = self._parse_result(self.sept_result)
                    if self.ann_result :
                        self.second_session_result = ann * 0.5 + sept * 0.5
                        self.second_session_result_bool = True 
                    else:
                        self.first_session_result = 0
                        self.first_session_result_bool = False
                except ValueError:
                    self.second_session_result = 0
                    self.second_session_result_bool = False
                    raise UserError(_('Cannot decode %s in September Result, please encode a Float eg "12.00".' % self.sept_result))