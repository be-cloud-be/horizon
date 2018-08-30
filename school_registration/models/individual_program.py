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

from openerp import api, fields, models, tools, _
from openerp.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

class IndividualProgram(models.Model):
    '''Individual Program'''
    _inherit='school.individual_program'
    
    @api.multi
    def register_pae(self):
        self.ensure_one()
        context = dict(self._context or {})
        _logger.info(context
        
        #if self.total_acquiered_credits < 45 :
        # Register all UE from bloc 1 that are not yet acquiered
        new_pae = self.env['school.individual_bloc'].create({
            'student_id' : context.get('default_student_id'),
            'program_id' : context.get('default_program_id'),
            'year_id' :  self.env.user.current_year_id.id,
            'source_bloc_id' : self.source_program_id.bloc_ids[0],
        })
            
        
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