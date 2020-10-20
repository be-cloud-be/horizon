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
    _inherit='school.individual_program'
    
    def _assign_cg(self, new_pae):
        cg_ids = []
        for group in new_pae.source_bloc_id.course_group_ids:
            # Check if cg already acquiered
            count = self.env['school.individual_course_group'].search_count([('student_id','=',self.student_id.id),('acquiered','=','A'),('source_course_group_id','=',group.id)])
            if count == 0 :
                _logger.info('Assign course groups : ' + group.ue_id + ' - ' +group.name)
                cg = new_pae.course_group_ids.create({'bloc_id': new_pae.id,'source_course_group_id': group.id, 'acquiered' : 'NA'})
                courses = []
                for course in group.course_ids:
                    _logger.info('assign course : ' + course.name)
                    courses.append((0,0,{'source_course_id': course.id}))
                _logger.info(courses)
                cg.write({'course_ids': courses})
            else :
                 _logger.info('Skip course groups : ' + group.ue_id + ' - ' +group.name)
    
    @api.multi
    def register_pae(self):
        self.ensure_one()
        context = dict(self._context or {})
        _logger.info(context)
        if not self.source_program_id:
            raise UserError(_("Pas de cycle théorique défini, impossible de proposer un PAE."))
        
        if self.total_acquiered_credits < 45 :
            # Register all UE from bloc 1 that are not yet acquiered
            new_pae = self.env['school.individual_bloc'].create({
                'student_id' : context.get('default_student_id'),
                'program_id' : context.get('default_program_id'),
                'year_id' :  self.env.user.current_year_id.id,
                'source_bloc_id' : self.source_program_id.bloc_ids[0].id,
            })
                
            self._assign_cg(new_pae)

        elif  self.total_acquiered_credits < 110 or len(self.source_program_id.bloc_ids) < 3 :
            # Register all UE that are not yet acquiered
            new_pae = self.env['school.individual_bloc'].create({
                'student_id' : context.get('default_student_id'),
                'program_id' : context.get('default_program_id'),
                'year_id' :  self.env.user.current_year_id.id,
                'source_bloc_id' : self.source_program_id.bloc_ids[1].id,
            })
                
            self._assign_cg(new_pae)
            
        else :
            # Register all UE that are not yet acquiered
            new_pae = self.env['school.individual_bloc'].create({
                'student_id' : context.get('default_student_id'),
                'program_id' : context.get('default_program_id'),
                'year_id' :  self.env.user.current_year_id.id,
                'source_bloc_id' : self.source_program_id.bloc_ids[2].id,
            })
                
            self._assign_cg(new_pae)
        
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'school.individual_bloc',
            'res_id' : new_pae.id,
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': False
        }
        return value