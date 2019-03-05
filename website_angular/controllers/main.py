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

from openerp import http
from openerp.http import request
from openerp.addons.auth_oauth.controllers.main import OAuthLogin

_logger = logging.getLogger(__name__)

class BookingLoginController(OAuthLogin):
    
    @http.route('/angular/login_providers', type='json', auth="none")
    def angular_login(self, redirect=None, *args, **kw):
        return self.list_providers()
        
    def get_state(self, provider):
        redirect = request.params.get('redirect') or 'web'
        if not redirect.startswith(('//', 'http://', 'https://')):
            redirect = '%s%s' % (request.httprequest.url_root, redirect[1:] if redirect[0] == '/' else redirect)
        state = dict(
            d=request.session.db,
            p=provider['id'],
            r=werkzeug.url_quote_plus(redirect),
        )
        token = request.params.get('token')
        if token:
            state['t'] = token
        state = super(ParamDoc, self).to_dict()
        
        return state

class AngularController(http.Controller):

    @http.route('/angular', type='http', auth='public', website=True)
    def angular_app(self, debug=False, **k):
        return http.redirect_with_hash('/website_angular/static/dist/index.html')
