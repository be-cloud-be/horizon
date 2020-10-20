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
import time
import werkzeug.utils
import json

from datetime import datetime, timedelta
import dateutil
import dateutil.parser
import dateutil.relativedelta

from odoo import api, fields
from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin as Home

_logger = logging.getLogger(__name__)

class BookingLoginController(Home):
    
    @http.route('/responsive/login_providers', type='json', auth="none")
    def booking_login_responsive(self, redirect=None, *args, **kw):
        return self.list_providers()

class BookingController(http.Controller):

    @http.route('/responsive/', type='http', auth='user', website=True)
    def responsive_index(self, debug=False, **k):
        values = {
            'user': request.env.user,
        }
        return request.render('website_horizon_responsive.index', values)

    @http.route('/responsive/profile', type='http', auth='user', website=True)
    def responsive_profile(self, debug=False, **k):
        values = {
            'user': request.env.user,
        }
        return request.render('website_horizon_responsive.profile', values)
        
    @http.route('/responsive/blocs', type='http', auth='user', website=True)
    def responsive_blocs(self, debug=False, **k):
        values = {
            'user': request.env.user,
            'blocs': request.env['school.individual_bloc'].search([('student_id','=',request.env.user.partner_id.id),('year_id','=',request.env.user.current_year_id.id)]),
            'display_results': request.env['ir.config_parameter'].sudo().get_param('school.display.results', '0'),
        }
        return request.render('website_horizon_responsive.blocs', values)
    
    @http.route('/responsive/booking_new', type='http', auth='user', website=True)
    def responsive_booking_new(self, debug=False, **k):
        
        values = {
            'user': request.env.user,
            'today' : fields.Datetime.to_string(datetime.today()),
            'tomorrow' : fields.Datetime.to_string(datetime.today() + timedelta(days=1))
        }
        return request.render('website_horizon_responsive.booking_new', values)
    
    @http.route('/responsive/booking_search', type='http', auth='user', website=True)
    def responsive_booking_search(self, debug=False, **k):
        values = {
            'user': request.env.user,
            'today' : fields.Datetime.to_string(datetime.today()),
            'tomorrow' : fields.Datetime.to_string(datetime.today() + timedelta(days=1))
        }
        return request.render('website_horizon_responsive.booking_search', values)
    
    @http.route('/responsive/bookings', type='http', auth='user', website=True)
    def responsive_bookings(self, debug=False, **k):
        start = fields.Datetime.to_string(datetime.today().replace(hour=0, minute=0, second=0))
        end = fields.Datetime.to_string(datetime.today().replace(hour=23, minute=59, second=59))
        event_fields = ['name','start','stop','allday','room_id','user_id','final_date','recurrency','categ_ids']
        domain = [
            ('start', '<=', end),    
            ('stop', '>=', start),
            ('user_id','=',request.uid),
        ]
        domain_next = [
            ('start', '<=', fields.Datetime.to_string(datetime.today().replace(hour=23, minute=59, second=59) + timedelta(days=1))),
            ('stop', '>=', fields.Datetime.to_string(datetime.today().replace(hour=0, minute=0, second=0) + timedelta(days=1))),
            ('user_id','=',request.uid),
        ]
        values = {
            'user': request.env.user,
            'bookings': request.env['calendar.event'].sudo().with_context({'virtual_id': True, 'tz':request.env.user.tz}).search(domain,event_fields,order='start asc'),
            'bookings_next': request.env['calendar.event'].sudo().with_context({'virtual_id': True,'tz':request.env.user.tz}).search(domain_next,event_fields,order='start asc'),
        }
        return request.render('website_horizon_responsive.bookings', values)
        
    @http.route('/responsive/delete/<int:booking_id>', type='http', auth='user', website=True)
    def responsive_delete_booking(self, booking_id, debug=False, **k):
        booking = request.env['calendar.event'].browse(booking_id)
        booking.unlink()
        return werkzeug.utils.redirect('/responsive/bookings')
        
        
    @http.route('/responsive/documents', type='http', auth='user', website=True)
    def responsive_documents(self, debug=False, **k):
        user = request.env.user
        partner_id = user.partner_id
        values = {
            'user': user,
            'official_document_ids' : partner_id.official_document_ids,
            'blocs' : request.env['school.individual_bloc'].search([('student_id','=',request.env.user.partner_id.id),('year_id','=',request.env.user.current_year_id.id)]),
        }
        return request.render('website_horizon_responsive.documents', values)