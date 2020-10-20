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

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

_logger = logging.getLogger(__name__)

class OfficialDocument(models.Model):
    '''Official Document'''
    _inherit = 'school.official_document'

    is_available_online = fields.Boolean(string="Is Available Online", default=False)
    
    online_attachment_id = fields.Many2one(comodel_name='ir.attachment', compute="_compute_online_attachment_id", store=True, readonly=False)
    
    @api.depends('attachment_ids')
    def _compute_online_attachment_id(self):
        for record in self:
            for a in record.attachment_ids:
                if a.mimetype == 'application/pdf':
                    record.online_attachment_id = a
                    break
    
    @api.constrains('is_available_online')
    def _check_is_available_online_constrains(self):
        for record in self:
            if record.is_available_online:
                if not record.is_available :
                    raise ValidationError("Document %s not yet available, plus upload your document first." % record.name)
                if not record.online_attachment_id :
                    raise ValidationError("No PDF document available on %s. Only PDF document can be available online, please upload one first." % record.name)