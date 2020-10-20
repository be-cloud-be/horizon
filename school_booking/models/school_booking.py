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

import pytz
from datetime import datetime, date, time, timedelta

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

def to_tz(datetime, tz):
    return pytz.UTC.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(tz).replace(tzinfo=None)

class Year(models.Model):
    _inherit = 'school.year'
    
    calendar_id = fields.Many2one('school.calendar', string='Default Calendar')

class SchoolCalendar(models.Model):
    _name = 'school.calendar'
    
    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active')
    
    year_id = fields.Many2one('school.year', string='Year', default=lambda self: self.env.user.current_year_id)
    from_date = fields.Date('From Date')
    to_date = fields.Date('From Date')
    leave_ids = fields.One2many('school.calendar.leave', 'calendar_id', 'Leaves',help='')
    
class SchoolLeave(models.Model):
    _name = 'school.calendar.leave'

    calendar_id = fields.Many2one('school.calendar', string='Calendar')

    from_date = fields.Date('From Date')
    to_date = fields.Date('From Date')

    partner_id = fields.Many2one('res.partner', string='Partner', help="If set, the leave is only for the specified partner.")
    asset_id = fields.Many2one('school.asset', string='Asset', help="If set, the leave is only for the asset.")
    category_id = fields.Many2one('school.asset.category', string='Category', help="If set, the leave is only for the asset of this category.")

class Event(models.Model):
    """ Model for School Event """
    _inherit = 'calendar.event'
    
    group_id = fields.Many2one('school.student_group', string='Group', ondelete='set null')
    yearly_booking_id = fields.Many2one('school.yearly_booking', string='Group', ondelete='set null')
    
    room_id = fields.Many2one('school.asset', string='Room', copy=False)
    asset_ids = fields.Many2many('school.asset', 'event_assets_ref','event_id','asset_id', string='Assets')
    
    main_categ_id = fields.Many2one('calendar.event.type', compute='_get_main_categ_id')
    
    @api.one
    def _get_main_categ_id(self):
        if self.categ_ids:
            self.main_categ_id = self.categ_ids[0]
    
    @api.one
    @api.constrains('room_id')
    def _check_room_quota(self):
        
        _logger.info('Check constraints _check_room_quota on record %s' % self.id)
        if self.room_id :
        
            # Admin is king
            
            if self.env.uid == 1 :
                return
    
            # Get user timezone
            
            utc_tz = pytz.UTC
            #user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'Europe/Brussels')
            user_tz = pytz.timezone('Europe/Brussels')
    
            # Prevent concurrent bookings

            domain = [('room_id','=',self.room_id.id), ('start', '<', self.stop_datetime), ('stop', '>', self.start_datetime)]
            conflicts_count = self.env['calendar.event'].sudo().with_context({'virtual_id': True}).search_count(domain)
            if conflicts_count > 1:
                raise ValidationError(_("Concurrent event detected - %s in %s") % (self.start_datetime, self.room_id.name))
    
            # Constraint not for employees and teatchers
    
            if self.env.user.has_group('school_management.group_employee'):
                return
    
            if self.env.user.has_group('school_management.group_teacher'):
                return
    
            # Constraint on student events
            
            student_event = self.env['ir.model.data'].xmlid_to_object('school_booking.school_student_event_type')
            
            if student_event in self.categ_ids:
                
                dt = to_tz(fields.Datetime.from_string(self.start_datetime),utc_tz)
                
                if dt.minute != 0 and dt.minute != 30 :
                    raise ValidationError(_("Invalid booking, please use standard booking."))
                
                now = to_tz(datetime.now(),user_tz)
                
                if now.hour < 19 and fields.Datetime.from_string(self.start_datetime).date() != now.date() :
                    raise ValidationError(_("You cannot book for the next day before 19h00."))
                
                if now.hour >= 19 and fields.Datetime.from_string(self.start_datetime).date() != now.date() and fields.Datetime.from_string(self.start_datetime).date() != (now + timedelta(days=1)).date() :
                    raise ValidationError(_("You can book only the next day (after 19h00)."))
                
                if dt < (datetime.now() + timedelta(minutes=-30)):
                    raise ValidationError(_("You cannot book in the past."))
                
                event_day = fields.Datetime.from_string(self.start_datetime).date()
                
                duration_list = self.env['calendar.event'].read_group([
                        ('user_id', '=', self.user_id.id), ('room_id','!=',False), ('categ_ids','in',student_event.id), ('start', '>=', fields.Datetime.to_string(event_day)), ('start', '<=', fields.Datetime.to_string(event_day + timedelta(days=1)))
                    ],['room_id','duration'],['room_id'])
                for duration in duration_list:
                    if duration['duration'] and duration['duration'] > 2:
                        raise ValidationError(_("You cannot book the room %s more than two hours per day") % (duration.get('room_id','')[1]))
                
                duration_list = self.env['calendar.event'].read_group([
                        ('user_id', '=', self.user_id.id), ('categ_ids','in',student_event.id), ('room_id','!=',False), ('start', '>=', fields.Datetime.to_string(event_day)), ('start', '<=', fields.Datetime.to_string(event_day + timedelta(days=1)))
                    ],['start_datetime','duration'],['start_datetime:day'])
                for duration in duration_list:
                    if duration['duration'] and duration['duration'] > 6:
                        raise ValidationError(_("You cannot book more than six hours per day - %s") % duration['start_datetime:day'])
                
                duration_list = self.env['calendar.event'].read_group([
                        ('user_id', '=', self.user_id.id), ('start', '>', fields.Datetime.now()), ('room_id','!=',False), ('categ_ids','in',student_event.id), ('start', '>=', fields.Datetime.to_string(event_day)), ('start', '<=', fields.Datetime.to_string(event_day + timedelta(days=1)))
                    ],['start_datetime','duration'],['start_datetime:day'])
                for duration in duration_list:
                    if duration['duration'] > 4:
                        raise ValidationError(_("You cannot book more than four hours in advance per day - %s") % duration['start_datetime:day'])
                        
                _logger.info('Check done')
                    
            
