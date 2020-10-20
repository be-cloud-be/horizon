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

class SchoolTeacherDesignation(models.Model):
    '''Teacher Designation'''
    _name = 'school.teacher.designation'
    _description = 'Teacher Designation'
    _inherit = ['mail.thread','school.year_sequence.mixin']
    
    _order = 'year_id desc,dgt_number desc'
    
    state = fields.Selection([
            ('draft','Draft'),
            ('active', 'Active'),
            ('canceled', 'Canceled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange',
        copy=False,
        help=" * The 'Draft' status is used when a designation is not validated yet.\n"
             " * The 'Active' status is when a designation is currently active.\n"
             " * The 'Canceled' status is used when a designation is canceled.")
    
    @api.multi
    def reset_to_draft(self):
        return self.write({'state': 'draft'})
    
    @api.multi
    def confirm(self):
        return self.write({'state': 'active'})
    
    @api.multi
    def cancel(self):
        return self.write({'state': 'canceled'})
    
    year_id = fields.Many2one('school.year', string='Year', required=True, default=lambda self: self.env.user.current_year_id)
    author_id = fields.Many2one('res.partner', string='Auteur', domain="[('type','=','contact')]", required=True, default=lambda self: self.env.user.partner_id)

    def _compute_default_number(self):
        numbers = self.env['school.teacher.designation'].search([('year_id', '=', self.env.user.current_year_id.id)])
        if len(numbers) > 0 :
            return max(numbers) + 1
        else :
            return 1

    dgt_number = fields.Integer(string="DGT PT ESA N°",default=_compute_default_number)
    dgt_state = fields.Selection([('A','Annule'),('R','Remplace'),('C','Complète')],string="Ce DGT",default='R')
    dgt_refereced_number = fields.Integer(string="le DGT") 
    
    type = fields.Selection([('R','Remplacement'),('V','Vacant')],'Type de désignation',default='V',required=True)
    fonction = fields.Selection([('C','Conférencier'),('E','Enseignant')], string='Fonction',default='C', required=True)
    cours = fields.Selection([('A','Artistique'),('T','Technique'),('G','Général')], string='Cours',default='T', required=True)
    experience = fields.Selection([('R','Requise'),('N','Non-requise')], string='Expérience utile',default='N', required=True)
    
    volume = fields.Char(string='Volume de charge',required=True)
    period_from = fields.Date(string='Pour la période du',required=True)
    period_to = fields.Date(string='au',required=True)
    
    replace_teacher_id = fields.Many2one('res.partner', string='En remplacement de', ondelete='restrict', domain=[('teacher','=',True)])
    replace_reason = fields.Char(string='Motif de l''absence')
    
    cgp_number = fields.Integer(string='CGP n°')
    cgp_date = fields.Date(string='Date du CGP')
    
    teacher_id = fields.Many2one('res.partner', string='Remplacant', ondelete='restrict', domain=[('teacher','=',True)])
    
    titre_capacite = fields.Char(string='Titre de capacité')
    date_capacite = fields.Date(string='Date d''obtention de l''expérience')
    appel_mb = fields.Boolean(string='A fait l''objet d''un appel au MB', default=False)
    candidature_mb = fields.Boolean(string='La personne a posé candidature', default=False)
    emploi_numero = fields.Integer(string='Numéro d''emploi')
    derogation = fields.Boolean(string='Dérogation nécessaire', default=False)
    derogation_reason = fields.Char(string='Raison de la dérogation')