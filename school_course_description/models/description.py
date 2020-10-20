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

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class CourseDocumentation(models.Model):
    '''CourseDocumentation'''
    _name = 'school.course_documentation'
    _description = 'Documentation about a course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    state = fields.Selection([
            ('draft','Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange',
        copy=False,
        help=" * The 'Draft' status is used when a new program is created and not published yet.\n"
             " * The 'Published' status is when a program is published and available for use.\n"
             " * The 'Archived' status is used when a program is obsolete and not publihed anymore.")
    
    course_id = fields.Many2one('school.course', string='Course', required=True)
    
    course_ids = fields.Many2many('school.course', 'school_doc_course_rel', 'doc_id', 'course_id', string='All Courses')
    
    name = fields.Char(related='course_id.name')
    
    remarks = fields.Char(string="Remarks")
    
    cycle_id = fields.Many2one(related='course_id.cycle_id')
    level = fields.Integer(related='course_id.level')
    course_group_id = fields.Many2one(related='course_id.course_group_id')
    
    @api.model
    def _needaction_domain_get(self):
        return [('state', '=', 'draft')]
    
    @api.onchange('course_id')
    def _onchange_course_id(self):
        self.write({
            'course_ids' : [(4,self.course_id)]
        })
    
    #@api.one
    #@api.constrains('state', 'course_id')
    #def _check_uniqueness(self):
    #    num_active = self.env['school.course_documentation'].search_count([['course_id', '=', self.course_id.id],['state','=','published']])
    #    if num_active > 1:
    #        raise ValidationError("Only on documentation shall be published at a given time")
    
    @api.multi
    def unpublish(self):
        return self.write({'state': 'draft'})
    
    @api.multi
    def publish(self):
        current = self.env['school.course_documentation'].search([['course_id', '=', self.course_id.id],['state','=','published']])
        if current:
            current[0].write({'state': 'archived'})
        return self.write({'state': 'published'})
    
    @api.multi
    def archive(self):
        return self.write({'state': 'archived'})

    author_id = fields.Many2one('res.users', string='Author')

    staff_ids = fields.Many2many('res.partner', 'school_desc_res_partner_rel', 'desc_id', 'res_partner_id', string='Teachers', domain=[('teacher', '=', 1)])
    credits = fields.Integer(related='course_id.credits', 
        help="""Le nombre de crédits correspondant à l'activité est également une information préremplie par l'administration, en se  référant au profil d'enseignement du cursus.
             ECTS signifie European Credits Transfer System, faisant référence au processus de Bologne. Au sens du décret paysage, 1 ECTS correspond à un investissement de temps de travail complet (cours, travaux, stages, travail personnel, évaluation,...) de la part de l'étudiant d'environ 30 heures.
             Un programme annuel de 60 crédits correspond donc en moyenne à un investissement de temps de travail complet de la part de l'étudiant d'environ 1800 heures.""")
    hours = fields.Integer(related='course_id.hours')
    weight = fields.Float(related='course_id.weight', 
        help="""Poids de l'évaluation de l'activité dans l'évaluation totale de l'unité. Cette pondération est définie par le tableau du règlement des études
            
            Crédits de              Coefficient               Cote finale sur
            l'activité              multiplicateur
            considérée             
                1 à 3                   1                       20
                4 à 6                   2                       40
                7 à 10                  3                       60
                11 à 14                 4                       80
                15 à 19                 5                       100
                20 et plus              6                       120
            (Domaine de la Musique)
                20 à 23 (DTAP)          6                       120
                24 à 29 (DTAP)          9                       180
                30 et plus (DTAP)       12                      240
            
            La pondération n'est évidemment pas nécessaire si l'UE ne comprend qu'une AA...
            Exemple:
            •	L'AA «banjo»vaut 23 crédits et possède donc une pondération 6 pour une cote finale d'évaluation sur 120;
            •	L'AA «écoute critique de la discographie consacrée au banjo» vaut 1 crédit et possède donc une pondération 1 pour une cote finale d'évaluation sur 20;
            •	L'UE «finalité principale» du « formation instrumentale / cordes / banjo» vaut au final 24 crédits avec une cote finale sur 140, somme des cotes des 2 AA. Cette cote finale est ensuite ramenée sur 20 pour l'encodage sur «Horizon»
            
            Note: Il est conservé la notion de pondération de l'UE au sein du programme du cycle à fin de calcul de la moyenne d'année ou du cycle. Cette moyenne ne conserve qu'un intérêt informatif pour les décisions de réussite de certaines unités d'enseignement par le jury de cycle ou pour l'attribution des mentions en fin de cycle. La pondération n'est pas demandée dans les descriptifs d'activités, elle est prévue par l'article 96 du Règlement des Études.	
            """)
    
    mandatory = fields.Boolean(string="Mandatory", default=True)
    
    schedule = fields.Selection([('Q1','Q1'),('Q2','Q2'),('Q1Q2','Q1 & Q2'),('O','Other')], string="Schedule", required=True, default="Q1")
    schedule_text = fields.Text(string="Schedule Text")
    
    content = fields.Text(string="Content")
    method = fields.Text(string="Method")
    learning_outcomes = fields.Text(string="Learning outcomes")
    references = fields.Text(string="References")
    evaluation_method = fields.Text(string="Evaluation method")
    #skills = fields.Text(string="Skills")
    pre_co_requiered = fields.Text(string="Pre-Co requiered")
    
    language = fields.Selection([('F','French'),('E','English'),('O','Other')], string="Language", required=True, default="F",
            help="""La langue d'enseignement et d'évaluation est en principe le français. L'obligation n'est totale que pour les masters à finalité didactique (pour lesquels une connaissance approfondie de la langue française est exigée). Des exceptions existent cependant au niveau des travaux de fin d'études, des enseignements de langues étrangères (évidemment...) et des activités d'intégration professionnelle.
                D'après le décret paysage (article 75), «de manière générale, toute activité d'apprentissage d'un cursus de premier ou deuxième cycle peut être organisée et évaluée dans une autre langue si elle est organisée également en français; cette obligation est satisfaite pour les options ou pour les activités au choix individuel de l'étudiant, s'il existe au moins un autre choix possible d'options ou d'activités organisées en français.»
                Pour le reste, «des activités peuvent être dispensées et évaluées dans une autre langue :
                1° dans le premier cycle d'études, à raison d'au plus un quart des crédits;
                2° pour les études menant au grade académique de master, sauf pour les crédits spécifiques à la finalité didactique, à raison de la moitié des crédits.»""")
    
    @api.model
    def default_get(self, fields):
        res = super(CourseDocumentation, self).default_get(fields)
        if 'author_id' in fields:
            res['author_id'] = self.env.user.id
        if 'staff_ids' in fields:
            if self.env.user.partner_id:
                res['staff_ids'] = [(6, False, [self.env.user.partner_id.id])]
        return res
    
class Course(models.Model):
    '''Course'''
    _inherit = 'school.course'
    
    documentation_id = fields.Many2one('school.course_documentation', string='Documentation', compute='compute_documentation_id', search='_search_documentation_id')
    
    documentation_ids = fields.Many2many('school.course_documentation', 'school_doc_course_rel', 'course_id', 'doc_id', string='All Docs')
    
    all_documentation_ids = fields.One2many('school.course_documentation', 'course_id', string='All Documentations')

    all_documentation_count = fields.Integer(string="Documentation Count", compute="_compute_count")
    
    @api.one
    @api.depends('all_documentation_ids')
    def _compute_count(self):
        self.all_documentation_count = len(self.documentation_ids)
    
    @api.one
    def compute_documentation_id(self):
        docs = self.documentation_ids.filtered(lambda r: r.state == 'published')
        if docs:
            self.documentation_id = docs[0]
        else:
            self.documentation_id = False
            
    @api.multi
    def _search_documentation_id(self, operator, value):
        if value == 'missing' :
            current_year_id = self.env.user.current_year_id
            current_program_ids = self.env['school.program'].search([['year_id', '=', current_year_id.id]])
            current_bloc_ids = current_program_ids.mapped('bloc_ids')
            current_ue_ids = current_bloc_ids.mapped('course_group_ids')
            current_course_ids = current_ue_ids.mapped('course_ids')
            recs = self.env['school.course_documentation'].search([('state', '=', 'published')]).mapped('course_ids')
            recs = current_course_ids - recs
            return [('id', 'in', [x.id for x in recs])]
        else :
            recs = self.env['school.course_documentation'].search([('state', '=', 'published')]).mapped('course_ids')
            if recs:
                if operator == '!=' :
                    return [('id', 'in', [x.id for x in recs])]
                else :
                    return [('id', 'not in', [x.id for x in recs])]
    