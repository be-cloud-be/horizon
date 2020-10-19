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

class CourseGroup(models.Model):
    '''Course Group'''
    _inherit = 'school.course_group'
    
    pre_requisit_ids = fields.One2many('school.prerequisit', 'course_id', 'Prerequisits')
    pre_requisit_course_ids = fields.One2many('school.course_group', string='Prerequisits', compute='_compute_pre_requisit_ids')

    co_requisit_ids = fields.One2many('school.corequisit', 'course_id', string='Corequisits')
    co_requisit_course_ids = fields.One2many('school.course_group', string='Corequisits', compute='_compute_co_requisit_ids')

    def _compute_pre_requisit_ids(self):
        for rec in self:
            ret_ids = []
            for pre_requisit in rec.pre_requisit_ids:
                ret_ids.append(pre_requisit.course_id.id)
            rec.pre_requisit_course_ids = ret_ids

    def _compute_co_requisit_ids(self):
        for rec in self:
            ret_ids = []
            for co_requisit in rec.co_requisit_ids:
                ret_ids.append(co_requisit.course_id.id)
            rec.co_requisit_ids = ret_ids
        
class PreRequisit(models.Model):
    '''PreRequisit'''
    _name = 'school.prerequisit'
    
    course_id = fields.Many2one('school.course_group', 'Course Group')
    preriquisit_id = fields.Many2one('school.course_group', 'Prerequisit')
    
class CoRequisit(models.Model):
    '''CoRequisit'''
    _name = 'school.corequisit'
    
    course_id = fields.Many2one('school.course_group', 'Course Group')
    coriquisit_id = fields.Many2one('school.course_group', 'Corequisit')