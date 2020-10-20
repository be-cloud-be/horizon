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

from odoo import api, fields, models, _
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)

class SplitUEWizard(models.TransientModel):
    _name = "school.split_cg_wizard"
    _description = "Split Course Group Wizard"
    
    source_course_group_id = fields.Many2one('school.course_group', string="Source Course Group")
    target_first_course_group_id = fields.Many2one('school.course_group', string="Source Course Group")
    target_second_course_group_id = fields.Many2one('school.course_group', string="Source Course Group")
    
    source_course_group_id_total_hours = fields.Integer(related='source_course_group_id.total_hours')
    source_course_group_id_total_credits = fields.Integer(related='source_course_group_id.total_credits')
    
    target_first_course_group_id_total_hours = fields.Integer(related='target_first_course_group_id.total_hours')
    target_first_course_group_id_total_credits = fields.Integer(related='target_first_course_group_id.total_credits')
    
    target_second_course_group_id_total_hours = fields.Integer(related='target_second_course_group_id.total_hours')
    target_second_course_group_id_total_credits = fields.Integer(related='target_second_course_group_id.total_credits')
    
    total_total_hours = fields.Integer(compute='_compute_totals')
    total_total_credits = fields.Integer(compute='_compute_totals')
    
    @api.depends('target_first_course_group_id','target_second_course_group_id')
    @api.one
    def _compute_totals(self):
        self.total_total_hours = self.target_first_course_group_id.total_hours + self.target_second_course_group_id.total_hours
        self.total_total_credits = self.target_first_course_group_id.total_credits + self.target_second_course_group_id.total_credits
    
    @api.onchange('source_course_group_id')
    def on_change_source_course_group_id(self):
        first = self.source_course_group_id.copy()
        second = self.source_course_group_id.copy()
        
        level = (first.level * 2 if first.level > 1 else 1) or 1
        
        first.write({
            'level' : level,
        })
        second.write({
            'level' : level + 1,
            'sequence' : first.sequence + 1,
        })
        
        for course in first.course_ids:
            if course.hours >= 30 :
                course.write({
                    'hours' : course.hours / 2,
                    'credits' : course.credits / 2,
                })
        
        for course in second.course_ids:
            if course.hours >= 30 :
                course.write({
                    'hours' : course.hours / 2,
                    'credits' : course.credits / 2,
                })
        
        self.update({
            'target_first_course_group_id': first,
            'target_second_course_group_id': second,
        })
    
    @api.multi
    def on_confirm(self):
        self.ensure_one()
        b_count = 0
        for bloc in self.source_course_group_id.bloc_ids:
            if bloc.year_id.id == 4:  # ie 2017-2018
                bloc.update({
                    'course_group_ids' : [
                        (3, self.source_course_group_id.id, _),
                        (4, self.target_first_course_group_id.id, _),
                        (4, self.target_second_course_group_id.id, _)
                    ]}
                )
                b_count += 1
        c_count = 0
        for compo in self.source_course_group_id.composite_parent_ids:
            compo.update({
                'course_group_ids' : [
                    (3, self.source_course_group_id.id, _),
                    (4, self.target_first_course_group_id.id, _),
                    (4, self.target_second_course_group_id.id, _)
                ]}
            )
            c_count += 1
            
        self.source_course_group_id.update({
            'active' : False,
        })
        return {'warning': {
            'title' : 'Blocs have been updated',
            'message' : '%d blocs and %d composits have been updated and the original course group has been archived.' % (b_count, c_count),
            }
        }
        
    @api.multi
    def on_cancel(self):
        self.ensure_one()
        self.target_first_course_group_id.unlink()
        self.target_second_course_group_id.unlink()
        return {'type': 'ir.actions.act_window_close'}
        
class CourseGroup(models.Model):
    '''Courses Group'''
    _inherit = 'school.course_group'
    
    @api.multi
    def on_split(self):
        value = {
                'name': _('Split Course Group Wizard'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'school.split_cg_wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context' : {'default_source_course_group_id': self.id},
        }
        return value