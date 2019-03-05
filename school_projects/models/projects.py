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

_logger = logging.getLogger(__name__)

class SchoolProject(models.Model):
    '''Student Project'''
    _name = 'school.project'
    _description = 'Student Project'
    _inherit = ['mail.thread','school.year_sequence.mixin']
    
    _order = 'responsible_id, year_id, name'
    
    state = fields.Selection([
            ('draft','Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange',
        copy=False,
        help=" * The 'Draft' status is used when a new project is created and not published yet.\n"
             " * The 'Published' status is when a project is published and available for use.\n"
             " * The 'Archived' status is used when a project is obsolete and not publihed anymore.")
    
    @api.multi
    def unpublish(self):
        return self.write({'state': 'draft'})
    
    @api.multi
    def publish(self):
        return self.write({'state': 'published'})
    
    @api.multi
    def archive(self):
        return self.write({'state': 'archived'})
    
    year_id = fields.Many2one('school.year', string='Year', required=True, default=lambda self: self.env.user.current_year_id)
    responsible_id = fields.Many2one('res.partner', string='Responsible', domain="[('type','=','contact')]", required=True, default=lambda self: self.env.user.partner_id)
    staff_ids = fields.Many2many('res.partner', 'group_staff_rel', 'group_id', 'staff_id', string='Staff', domain="[('type','=','contact')]")
    
    type = fields.Selection([('M','Main'),('S','Secondary')],string="Project Type",default="M", required=True)
    
    title = fields.Char(string='Title')
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    short_name = fields.Char(string='Name', compute='_compute_name', store=True) 
    
    @api.one
    @api.depends('year_id', 'title', 'responsible_id')
    def _compute_name(self):
        self.name = '%s - %s - %s' % (self.year_id.short_name, self.responsible_id.name, self.title)
        self.short_name = self.title

    participant_ids = fields.Many2many('res.partner', 'school_group_participants_rel', 'group_id', 'res_partner_id', string='Participipants', domain="[('type', '=', 'contact')]")
    participant_count = fields.Integer(string="Participant Count")
        
    @api.onchange('course_ids')
    def onchange_course_ids(self):
        if self.course_ids:
            if self.type == 'L':
                self.individual_course_ids = self.env['school.individual_course'].search([('year_id','=',self.year_id.id),('source_course_id','in',self.course_ids.ids)])
            elif self.type == 'F':
                for ic in self.individual_course_ids:
                    if ic.source_course_id not in self.course_ids:
                        raise ValidationError(_('Individual Course %s does not match the course selection, please remove it before changing the Courses' % (ic.name)))
            else:
                raise ValidationError(_('Cannot select Course on this type of group.'))
            return {
                'domain': {'individual_course_ids': [('year_id','=',self.year_id.id),('source_course_id', '=', self.course_ids.ids)]}
            }

    @api.onchange('participant_ids')
    def onchange_picked_participant_ids(self):
        self.participant_count = len(self.participant_ids)
            
    @api.multi
    def action_participants_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Participants',
            'res_model': 'res.partner',
            'domain': [('id', 'in', self.participant_ids.ids)],
            'view_mode': 'tree',
        }
        
    attachment_ids = fields.Many2many('ir.attachment','project_ir_attachment_rel', 'project_id','ir_attachment_id', 'Attachments')
    attachment_count = fields.Integer(compute='_compute_attachment_count', string='# Attachments')

    @api.one
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        self.attachment_count = len(self.attachment_ids)