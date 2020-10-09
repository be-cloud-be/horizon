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

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

class IndividualProgram(models.Model):
    '''Individual Program'''
    _name='school.individual_program'
    _description='Individual Program'
    _inherit = ['mail.thread']
    
    _order = 'name'

    active = fields.Boolean(string='Active', help="The active field allows you to hide the course group without removing it.", default=True, copy=False)

    name = fields.Char(compute='_compute_name',string='Name', readonly=True, store=True)
    
    year_id = fields.Many2one('school.year', string='Registration Year', default=lambda self: self.env.user.current_year_id)
    
    student_id = fields.Many2one('res.partner', string='Student', domain="[('student', '=', '1')]", required=True)
    student_name = fields.Char(related='student_id.name', string="Student Name", readonly=True, store=True)
    
    image = fields.Binary('Image', attachment=True, related='student_id.image')
    image_medium = fields.Binary('Image', attachment=True, related='student_id.image_medium')
    image_small = fields.Binary('Image', attachment=True, related='student_id.image_small')
    
    source_program_id = fields.Many2one('school.program', string="Source Program", ondelete="restrict")
    
    cycle_id = fields.Many2one('school.cycle', related='source_program_id.cycle_id', string='Cycle', store=True, readonly=True)
    
    speciality_id = fields.Many2one('school.speciality', related='source_program_id.speciality_id', string='Speciality', store=True, readonly=True)
    domain_id = fields.Many2one(related='speciality_id.domain_id', string='Domain',store=True)
    section_id = fields.Many2one(related='speciality_id.section_id', string='Section',store=True)
    track_id = fields.Many2one(related='speciality_id.track_id', string='Track',store=True)
    
    required_credits = fields.Integer(related='cycle_id.required_credits',string='Requiered Credits')
    
    course_group_ids = fields.One2many('school.course_group', string='Courses Groups', compute='_compute_ind_course_group_ids')
    
    ind_course_group_ids = fields.One2many('school.individual_course_group', string='Ind Courses Groups', compute='_compute_ind_course_group_ids')
    
    @api.one
    def _compute_ind_course_group_ids(self):
        course_group_ids = False
        for bloc in self.source_program_id.bloc_ids:
            if course_group_ids :
                course_group_ids |= bloc.course_group_ids
            else :
                course_group_ids = bloc.course_group_ids
        self.course_group_ids = course_group_ids
        self.ind_course_group_ids = self.env['school.individual_course_group'].search([('bloc_id','in',self.bloc_ids.ids)])
    
    @api.one
    @api.depends('cycle_id.name','speciality_id.name','student_id.name')
    def _compute_name(self):
        self.name = "%s - %s - %s" % (self.student_id.name,self.cycle_id.name,self.speciality_id.name)
        
    bloc_ids = fields.One2many('school.individual_bloc', 'program_id', string='Individual Blocs')
    
    highest_level =  fields.Integer(compute='_compute_highest_level',string='Highest Level', store=True)

    @api.one
    @api.depends('bloc_ids.source_bloc_level')
    def _compute_highest_level(self):
        levels = self.bloc_ids.mapped('source_bloc_level')
        if levels:
            self.highest_level = max(levels)
        else:
            self.highest_level = 0

class IndividualBloc(models.Model):
    '''Individual Bloc'''
    _name='school.individual_bloc'
    _description='Individual Bloc'
    _inherit = ['mail.thread','school.year_sequence.mixin']
    
    _order = 'year_id, source_bloc_level desc, source_bloc_name'
    
    active = fields.Boolean(string='Active', help="The active field allows you to hide the course group without removing it.", default=True, copy=False)
    
    name = fields.Char(compute='_compute_name',string='Name', readonly=True, store=True)
    
    program_id = fields.Many2one('school.individual_program', string='Individual Program', required=True)
    
    year_id = fields.Many2one('school.year', string='Year')
    
    is_final_bloc = fields.Boolean(string='Is final bloc')
    
    student_id = fields.Many2one(related='program_id.student_id', string='Student', domain="[('student', '=', '1')]", readonly=True, store=True)
    student_name = fields.Char(related='student_id.name', string="Student Name", readonly=True, store=True)
    
    source_bloc_id = fields.Many2one('school.bloc', string="Source Bloc", ondelete="restrict")
    source_bloc_name = fields.Char(related='source_bloc_id.name', string="Source Bloc Name", readonly=True, store=True)
    source_bloc_title = fields.Char(related='source_bloc_id.title', string="Source Bloc Title", readonly=True, store=True)
    source_bloc_level = fields.Selection([('0','Free'),('1','Bac 1'),('2','Bac 2'),('3','Bac 3'),('4','Master 1'),('5','Master 2'),('6','Agregation'),],related='source_bloc_id.level', string="Source Bloc Level", readonly=True, store=True)
    
    source_bloc_domain_id = fields.Many2one('school.domain',compute='compute_speciality', string='Domain', readonly=True, store=True)
    source_bloc_speciality_id = fields.Many2one('school.speciality',compute='compute_speciality', string='Speciality', readonly=True, store=True)
    source_bloc_section_id = fields.Many2one('school.section',compute='compute_speciality', string='Section', readonly=True, store=True)
    source_bloc_track_id = fields.Many2one('school.track',compute='compute_speciality', string='Track', readonly=True, store=True)
    source_bloc_cycle_id = fields.Many2one('school.cycle',compute='compute_speciality', string='Cycle', readonly=True, store=True)
    
    @api.depends('source_bloc_id.speciality_id','program_id.speciality_id')
    @api.multi
    def compute_speciality(self):
        for bloc in self:
            if bloc.source_bloc_id.speciality_id :
                bloc.source_bloc_speciality_id = bloc.source_bloc_id.speciality_id
                bloc.source_bloc_domain_id = bloc.source_bloc_id.domain_id
                bloc.source_bloc_section_id = bloc.source_bloc_id.section_id
                bloc.source_bloc_track_id = bloc.source_bloc_id.track_id
            elif bloc.program_id.speciality_id :
                bloc.source_bloc_speciality_id = bloc.program_id.speciality_id
                bloc.source_bloc_domain_id = bloc.program_id.domain_id
                bloc.source_bloc_section_id = bloc.program_id.section_id
                bloc.source_bloc_track_id = bloc.program_id.track_id
    
    image = fields.Binary('Image', attachment=True, related='student_id.image')
    image_medium = fields.Binary('Image', attachment=True, related='student_id.image_medium')
    image_small = fields.Binary('Image', attachment=True, related='student_id.image_small')
    
    course_group_ids = fields.One2many('school.individual_course_group', 'bloc_id', string='Courses Groups', track_visibility='onchange')
    
    total_credits = fields.Integer(compute='_get_courses_total', string='Credits')
    total_hours = fields.Integer(compute='_get_courses_total', string='Hours')
    total_weight = fields.Float(compute='_get_courses_total', string='Weight')

    # @api.onchange('source_bloc_id')
    # @api.depends('course_group_ids')
    # def assign_source_bloc(self):
    #     cg_ids = []
    #     for group in self.source_bloc_id.course_group_ids:
    #         _logger.info('assign course groups : ' + group.name)
    #         cg = self.course_group_ids.create({'bloc_id': self.id,'source_course_group_id': group.id, 'acquiered' : 'NA'}) # TODO FIX DEPENDENCIE TO EVALUATION
    #         courses = []
    #         for course in group.course_ids:
    #             _logger.info('assign course : ' + course.name)
    #             courses.append((0,0,{'source_course_id': course.id}))
    #         _logger.info(courses)
    #         cg.write({'course_ids': courses})

    @api.depends('course_group_ids.total_hours','course_group_ids.total_credits','course_group_ids.total_weight','course_group_ids.is_ghost_cg')
    @api.one
    def _get_courses_total(self):
        _logger.debug('Trigger "_get_courses_total" on Course Group %s' % self.name)
        self.total_hours = sum(course_group.total_hours for course_group in self.course_group_ids if not course_group.is_ghost_cg)
        self.total_credits = sum(course_group.total_credits for course_group in self.course_group_ids if not course_group.is_ghost_cg)
        self.total_weight = sum(course_group.total_weight for course_group in self.course_group_ids if not course_group.is_ghost_cg)

    @api.one
    @api.depends('year_id.name','student_id.name')
    def _compute_name(self):
        self.name = "%s - %s" % (self.year_id.name,self.student_id.name)
    
    _sql_constraints = [
	        ('uniq_student_bloc', 'unique(year_id, student_id, source_bloc_id)', 'This individual bloc already exists.'),
    ]
    
    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(IndividualBloc, self).message_get_suggested_recipients()
        try:
            for bloc in self:
                if bloc.student_id:
                    bloc._message_add_suggested_recipient(recipients, partner=bloc.student_id, reason=_('Student'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients
          
    course_count = fields.Integer(compute='_compute_course_count', string="Course")

    @api.multi
    def _compute_course_count(self):
        for bloc in self:
            bloc.course_count = self.env['school.individual_course'].search_count([('bloc_id', '=', bloc.id)])

    @api.multi
    def open_courses(self):
        """ Utility method used to add an "Open Courses" button in bloc views """
        self.ensure_one()
        return {
            'name': _('Courses'),
            'domain': [('bloc_id', '=', self.id)],
            'res_model': 'school.individual_course',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
        }

class IndividualCourseGroup(models.Model):
    '''Individual Course Group'''
    _name='school.individual_course_group'
    _description='Individual Course Group'
    _inherit = ['mail.thread','school.year_sequence.mixin']
    
    _order = 'year_id, sequence'
    
    name = fields.Char(related="source_course_group_id.name", readonly=True) #, store=True)
    ue_id = fields.Char(related="source_course_group_id.ue_id", readonly=True)# , store=True)
    title = fields.Char(related="source_course_group_id.title", readonly=True, store=True)
    
    sequence = fields.Integer(related="source_course_group_id.sequence", readonly=True, store=True)
    
    year_id = fields.Many2one(related="bloc_id.year_id", string='Year', store=True)
    student_id = fields.Many2one(related="bloc_id.student_id", string='Student', store=True, domain=[('student', '=', True)])
    teacher_id = fields.Many2one('res.partner', string='Teacher', store=True, domain=[('teacher', '=', True)])
    
    image = fields.Binary('Image', attachment=True, related='student_id.image')
    image_medium = fields.Binary('Image', attachment=True, related='student_id.image_medium')
    image_small = fields.Binary('Image', attachment=True, related='student_id.image_small')
    
    source_course_group_id = fields.Many2one('school.course_group', string="Source Course Group", ondelete="restrict")
    
    bloc_id = fields.Many2one('school.individual_bloc', string="Bloc", ondelete='cascade', readonly=True)

    source_bloc_id = fields.Many2one('school.bloc', string="Source Bloc", related='bloc_id.source_bloc_id', readonly=True, store=True)
    source_bloc_name = fields.Char(related='bloc_id.source_bloc_name', string="Source Course Bloc Name", readonly=True, store=True)
    source_bloc_level = fields.Selection([('0','Free'),('1','Bac 1'),('2','Bac 2'),('3','Bac 3'),('4','Master 1'),('5','Master 2'),],related='bloc_id.source_bloc_level', string="Source Course Bloc Level", readonly=True, store=True)
    
    source_bloc_domain_id = fields.Many2one(related='bloc_id.source_bloc_domain_id', string='Domain', readonly=True, store=True)
    source_bloc_speciality_id = fields.Many2one(related='bloc_id.source_bloc_speciality_id', string='Speciality', readonly=True, store=True)
    source_bloc_section_id = fields.Many2one(related='bloc_id.source_bloc_section_id', string='Section', readonly=True, store=True)
    source_bloc_track_id = fields.Many2one(related='bloc_id.source_bloc_track_id', string='Track', readonly=True, store=True)
    source_bloc_cycle_id = fields.Many2one(related='bloc_id.source_bloc_cycle_id', string='Cycle', readonly=True, store=True)

    course_ids = fields.One2many('school.individual_course', 'course_group_id', string='Courses',track_visibility='onchange')
    
    is_ghost_cg = fields.Boolean(string='Is Ghost Course Group', default=False)
    
    total_credits = fields.Integer(compute='_get_courses_total', string='Credits', store=True)
    total_hours = fields.Integer(compute='_get_courses_total', string='Hours', store=True)
    total_weight = fields.Float(compute='_get_courses_total', string='Total Weight', store=True)
    weight = fields.Integer(related="source_course_group_id.weight",string='Weight', store=True)
    
    ue_id =  fields.Char(related="source_course_group_id.ue_id", readonly=True)
    
    @api.onchange('source_course_group_id')
    def onchange_source_cg(self):
        courses = []
        for course in self.source_course_group_id.course_ids:
            _logger.info('assign course : ' + course.name)
            courses.append((0,0,{'source_course_id':course.id}))
        _logger.info(courses)
        self.update({'course_ids': courses})

    @api.depends('course_ids.hours','course_ids.credits','course_ids.weight')
    @api.one
    def _get_courses_total(self):
        _logger.debug('Trigger "_get_courses_total" on Course Group %s' % self.name)
        self.total_hours = sum(course.hours for course in self.course_ids)
        self.total_credits = sum(course.credits for course in self.course_ids)
        self.total_weight = sum(course.weight for course in self.course_ids)

class IndividualCourse(models.Model):
    '''Individual Course'''
    _name = 'school.individual_course'
    _description = 'Individual Course'
    _inherit = ['mail.thread','school.year_sequence.mixin','ir.needaction_mixin']
    
    _order = 'sequence'
    
    name = fields.Char(related="source_course_id.name", readonly=True, store=True)
    title = fields.Char(related="source_course_id.title", readonly=True, store=True)
    level = fields.Integer(related="source_course_id.level", readonly=True)
    
    sequence = fields.Integer(related="source_course_id.sequence", readonly=True, store=True)
    
    year_id = fields.Many2one('school.year', related="course_group_id.bloc_id.year_id",store=True)
    student_id = fields.Many2one('res.partner', related="course_group_id.bloc_id.student_id",store=True)
    
    teacher_id = fields.Many2one('res.partner', string='Teacher', compute='compute_teacher_id', store=True)
    teacher_choice_id = fields.Many2one('res.partner', string='Teacher Choice', domain=[('teacher', '=',1)])
    
    @api.depends('teacher_choice_id','source_course_id.teacher_ids')
    @api.one
    def compute_teacher_id(self):
        if self.teacher_choice_id:
            self.teacher_id = self.teacher_choice_id
        elif len(self.source_course_id.teacher_ids) == 1:
            self.teacher_id = self.source_course_id.teacher_ids[0]
        else:
            self.teacher_id = None

    @api.one
    def guess_teacher_id(self):
        old_course = self.env['school.individual_course'].search([('student_id','=',self.student_id.id),('year_id','=',self.year_id.previous.id),('title', '=', self.source_course_id.title)])
        if len(old_course) == 1 and old_course.teacher_id:
            self.teacher_id = old_course.teacher_id

    image = fields.Binary('Image', attachment=True, related='student_id.image')
    image_medium = fields.Binary('Image', attachment=True, related='student_id.image_medium')
    image_small = fields.Binary('Image', attachment=True, related='student_id.image_small')

    url_ref = fields.Char(related="source_course_id.url_ref", readonly=True)

    credits = fields.Integer(related="source_course_id.credits", readonly=True)
    hours = fields.Integer(related="source_course_id.hours", readonly=True)
    weight =  fields.Float(related="source_course_id.weight", readonly=True, default=1.00)
    
    dispense = fields.Boolean(string="Dispensed",default=False,track_visibility='onchange')
    
    source_course_id = fields.Many2one('school.course', string="Source Course", auto_join=True, ondelete="restrict")
    
    source_bloc_id = fields.Many2one('school.bloc', string="Source Bloc", related='course_group_id.bloc_id.source_bloc_id', readonly=True, store=True)
    source_bloc_name = fields.Char(related='course_group_id.bloc_id.source_bloc_name', string="Source Course Bloc Name", readonly=True, store=True)
    source_bloc_level = fields.Selection([('0','Free'),('1','Bac 1'),('2','Bac 2'),('3','Bac 3'),('4','Master 1'),('5','Master 2'),],related='course_group_id.bloc_id.source_bloc_level', string="Source Course Bloc Level", readonly=True, store=True)
    
    source_bloc_domain_id = fields.Many2one(related='course_group_id.bloc_id.source_bloc_domain_id', string='Domain', readonly=True, store=True)
    source_bloc_speciality_id = fields.Many2one(related='course_group_id.bloc_id.source_bloc_speciality_id', string='Speciality', readonly=True, store=True)
    source_bloc_section_id = fields.Many2one(related='course_group_id.bloc_id.source_bloc_section_id', string='Section', readonly=True, store=True)
    source_bloc_track_id = fields.Many2one(related='course_group_id.bloc_id.source_bloc_track_id', string='Track', readonly=True, store=True)
    source_bloc_cycle_id = fields.Many2one(related='course_group_id.bloc_id.source_bloc_cycle_id', string='Cycle', readonly=True, store=True)
    
    course_group_id = fields.Many2one('school.individual_course_group', string='Course Groups', ondelete='cascade', readonly=True)
    bloc_id = fields.Many2one('school.individual_bloc', string='Bloc', related='course_group_id.bloc_id', readonly=True, store=True)
    
    @api.multi
    def open_program(self):
        """ Utility method used to add an "Open Bloc" button in course views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'school.individual_bloc',
                'view_mode': 'form',
                'res_id': self.bloc_id.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}
    
class IndividualCourseProxy(models.Model):
    _name = 'school.individual_course_proxy'
    _auto = False
    _inherit = ['school.year_sequence.mixin']

    name = fields.Char(string="Name", readonly=True)
    title = fields.Char(string="Title", readonly=True)
    
    year_id = fields.Many2one('school.year', string='Year', readonly=True)
    teacher_id = fields.Many2one('res.partner', string='Teacher', readonly=True)
    source_course_id = fields.Many2one('school.course', string="Source Course", readonly=True)
    
    student_count = fields.Integer(string="Student Count", readonly=True)

    def init(self, cr):
        """ School Individual Course Proxy """
        tools.drop_view_if_exists(cr, 'school_individual_course_proxy')
        cr.execute(""" CREATE VIEW school_individual_course_proxy AS (
            SELECT
                CAST(CAST(school_individual_course.year_id AS text)||
                CAST(school_individual_course.teacher_id AS text)||
                CAST(school_individual_course.source_course_id AS text) AS BIGINT) as id,
                school_individual_course.name,
                school_individual_course.title,
                school_individual_course.year_id,
                school_individual_course.teacher_id,
                school_individual_course.source_course_id,
                COUNT(CAST(CAST(school_individual_course.year_id AS text)||
                CAST(school_individual_course.teacher_id AS text)||
                CAST(school_individual_course.source_course_id AS text) AS BIGINT)) as student_count
            FROM
                school_individual_course
            WHERE
                school_individual_course.teacher_id IS NOT NULL
            GROUP BY CAST(CAST(school_individual_course.year_id AS text)||
                CAST(school_individual_course.teacher_id AS text)||
                CAST(school_individual_course.source_course_id AS text) AS BIGINT),
                school_individual_course.name,
                school_individual_course.title,
                school_individual_course.year_id,
                school_individual_course.teacher_id,
                school_individual_course.source_course_id
        )""")
        
        
    @api.multi
    def edit_course(self):
        self.ensure_one()
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'school.individual_course',
            'view_id': False,
            'context': dict(self._context or {}),
            'type': 'ir.actions.act_window',
            'search_view_id': False
        }
        return value