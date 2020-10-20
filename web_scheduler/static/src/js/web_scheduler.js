/*
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
*/
odoo.define('web_scheduler.SchedulerView', function (require) {
    "use strict";
    
    var core = require('web.core');
    var _t = core._t;
    var _lt = core._lt;
    
    var Model = require('web.DataModel');
    var CalendarView = require('web.CalendarView');
    
    CalendarView.include({
         
        view_loading: function (fv) {
            var attrs = fv.arch.attrs,
            self = this;
            self.scheduler_group = attrs.scheduler_group;
            self.scheduler_domain = attrs.scheduler_domain;
            self.slot_duration = attrs.slot_duration;
            self._super(fv);
        },
        
        render_buttons: function($node) {
            var self = this;
            self._super($node);
            if(self.scheduler_group) {
                var bindCalendarButton = function(selector, arg1, arg2) {
                    self.$buttons.on('click', selector, _.bind(self.$calendar.fullCalendar, self.$calendar, arg1, arg2));
                }
                bindCalendarButton('.o_calendar_button_timeline', 'changeView', 'timelineDay');
            }
        },
         
        calendarMiniChanged: function (context) {
            return function(datum,obj) {
                var curView = context.$calendar.fullCalendar('getView');
                var curDate = moment([obj.currentYear , obj.currentMonth, obj.currentDay]);
                
                if (curView.name != "timelineDay") {
                    context.$calendar.fullCalendar('changeView','timelineDay');
                }
                context.$calendar.fullCalendar('gotoDate', curDate);
            };
        },
        
        get_fc_init_options: function () {
            var self = this;
            if(self.scheduler_group) {
                self.resourceObjects = [];
                var ret = $.extend(this._super(),{
                    
                    defaultView: (this.mode == "day") ? "agendaDay" : "timelineDay",

                    viewRender: function(view) {
                        var mode;
                        switch(view.name) {
                            case "month":
                                mode = "month";
                                break;
                            case "agendaWeek":
                                mode = "week" ;
                                break;
                            case "timelineDay":
                                mode = "timeline" ;
                                break;
                            default:
                                mode = "day" ;
                        }
                        
                        if(self.$buttons !== undefined) {
                            self.$buttons.find('.active').removeClass('active');
                            self.$buttons.find('.o_calendar_button_' + mode).addClass('active');
                        }
        
                        var title = self.title + ' (' + ((mode === "week")? _t("Week ") : "") + view.title + ")"; 
                        self.set({'title': title});
        
                        self.$calendar.fullCalendar('option', 'height', Math.max(290, parseInt(self.$('.o_calendar_view').height())-30));
        
                        setTimeout(function() {
                            var $fc_view = self.$calendar.find('.fc-view');
                            var width = $fc_view.find('> table').width();
                            $fc_view.find('> div').css('width', (width > $fc_view.width())? width : '100%'); // 100% = fullCalendar default
                        }, 0);
                    },
                    
                    resources: function(callback) {
                        var scheduler_group = self.fields[self.scheduler_group];
                        new Model(scheduler_group.relation).query(["name"]).filter(self.scheduler_domain).all().then(function(result) {
                            _.each(result, function(item) {
                                self.resourceObjects.push({
                                    id : item.id,
                                    title : item.name,
                                });
                            });
                        }).done(function() {
                            callback(self.resourceObjects);
                        });
                    },
                    
                    refetchResourcesOnNavigate : false,
                    
                });
                ret.views = $.extend(ret.views, {
                    timelineDay: { // name of view
                        titleFormat: 'DD/MM/YYYY',
                        minTime: {hours : 7},
                        maxTime: {hours : 23},
                        slotDuration: {hours : 1},
                    },    
                });
                return ret;
            }
            return this._super();
        },
        
        event_data_transform: function(evt) {
            var self = this;
            if(self.scheduler_group){
                return $.extend(self._super(evt),{
                    'resourceId' : evt[self.scheduler_group][0],
                });
            } else {
                return self._super(evt);
            }
        },
        
        
        /**
         * Transform fullcalendar event object to OpenERP Data object
         */
        get_event_data: function(event) {
            var self = this;
            var data = self._super(event);
            // fetch the ressource if available
            data.room_id = event.resource.id;
            return data;
        },
        
    });
});
