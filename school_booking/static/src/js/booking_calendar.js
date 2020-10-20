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
odoo.define('school_booking.booking_calendar', function (require) {
    
    "use strict";
    
    var core = require('web.core');
    var _t = core._t;
    var _lt = core._lt;
    
    var Model = require('web.DataModel');
    var data = require('web.data');
    var CalendarView = require('web.CalendarView');
    var BaseCalendar = require('web.CalendarView');
    var widgets = require('web.widgets');
    
    function reload_favorite_list(result) {
        var self = result;
        var current = result;
        if (result.view) {
            self = result.view;
        }
        return new Model("res.users")
        .query(["partner_id"])
        .filter([["id", "=", self.dataset.context.uid]])
        .first()
        .done(function(result) {
            var sidebar_items = {};
            var filter_value = result.partner_id[0];
            var filter_item = {
                value: filter_value,
                label: result.partner_id[1] + _lt(" [Me]"),
                color: self.get_color(filter_value),
                avatar_model: self.avatar_model,
                is_checked: true,
                is_remove: false,
            };
            sidebar_items[filter_value] = filter_item;
    
            filter_item = {
                value: -1,
                label: _lt("Everybody's calendars"),
                color: self.get_color(-1),
                avatar_model: self.avatar_model,
                is_checked: false
            };
            sidebar_items[-1] = filter_item;
            //Get my coworkers/contacts
            new Model("calendar.contacts").query(["partner_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
                _.each(result, function(item) {
                    filter_value = item.partner_id[0];
                    filter_item = {
                        value: filter_value,
                        label: item.partner_id[1],
                        color: self.get_color(filter_value),
                        avatar_model: self.avatar_model,
                        is_checked: true
                    };
                    sidebar_items[filter_value] = filter_item;
                });
            }).done(function () {
                // Get my assets
                new Model("school.calendar.assets").query(["asset_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
                    _.each(result, function(item) {
                        filter_value = item.asset_id[0];
                        filter_item = {
                            value: filter_value,
                            label: item.asset_id[1],
                            color: self.get_color(filter_value),
                            avatar_model: self.avatar_model,
                            is_checked: true
                        };
                        sidebar_items[filter_value] = filter_item;
                    });
        
                    self.all_filters = sidebar_items;
                    self.now_filter_ids = $.map(self.all_filters, function(o) { return o.value; });
                    
                    self.sidebar.filter.events_loaded(self.get_all_filters_ordered());
                    self.sidebar.filter.set_filters();
                    self.sidebar.filter.add_favorite_calendar();
                    self.sidebar.filter.destroy_filter();
                }).done(function () {
                    self.$calendar.fullCalendar('refetchEvents');
                    if (current.ir_model_m2o) {
                        current.ir_model_m2o.set_value(false);
                    }
                    if (current.ir_asset_m2o) {
                        current.ir_asset_m2o.set_value(false);
                    }
                });
            });
        });
    }
    
    widgets.SidebarFilter.include({
            
        initialize_m2o: function() {
            this._super();
            var self = this;
            this.dfm.extend_field_desc({
                asset_id : {
                    relation: "school.asset",
                },
            });
            var FieldMany2One = core.form_widget_registry.get('many2one');
            this.ir_asset_m2o = new FieldMany2One(self.dfm, {
                attrs: {
                    class: 'o_add_asset_calendar',
                    name: "asset_id",
                    type: "many2one",
                    options: '{"no_open": True}',
                    placeholder: _t("Add Asset Calendar"),
                },
            });
            this.ir_asset_m2o.appendTo(this.$el);
            this.ir_asset_m2o.on('change:value', self, function() {
                // once selected, we reset the value to false.
                if (self.ir_asset_m2o.get_value()) {
                    self.add_filter_assets();
                }
            });
        },
        
        add_filter_assets : function() {
            var self = this;
            var defs = [];
            defs.push(new Model("school.asset")
            .query(["asset_id"])
            .filter([["id", "=",this.view.dataset.context.uid]])
            .first()
            .done(function(result){
                var asset_id = self.ir_asset_m2o.get_value();
                self.ds_message = new data.DataSetSearch(self, 'school.calendar.assets');
                defs.push(self.ds_message.call("create", [{'asset_id': asset_id}]));
            }));
            return $.when.apply(null, defs).then(function() {
                return reload_favorite_list(self);
            });
        },
       
    });
    
    CalendarView.include({
        
        extraSideBar: function() {
            var result = this._super();
            if (this.useContacts) {
                return result.then(reload_favorite_list(this));
            }
            return result;
        },
        
        _do_search: function(domain, context, _group_by) {
            this._super(domain, context, _group_by);
            
            var self = this;
            if (! self.all_filters) {
                self.all_filters = {};
            }
    
            if (! _.isUndefined(this.asset_event_source)) {
                this.$calendar.fullCalendar('removeEventSource', this.asset_event_source);
            }
            this.asset_event_source = {
                
                events: function(start, end, timezone, callback) {
                    // catch invalid dates (start/end dates not parseable yet)
                    // => ignore request
                    if (isNaN(start) || isNaN(end)) {
                        return;
                    }
    
                    var current_event_source = self.asset_event_source;
                    var event_domain = self.get_range_domain(domain, start, end);
                    var asset_ids = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.asset_value; }});
                    if (!_.isEmpty(asset_ids)) {
                        event_domain = new data.CompoundDomain(
                            event_domain,
                            ['|',['asset_ids', 'in', asset_ids],['room_id', 'in', asset_ids]]
                        );
                    }
    
                    // read_slice is launched uncoditionally, when quickly
                    // changing the range in the calender view, all of
                    // these RPC calls will race each other. Because of
                    // this we keep track of the current range of the
                    // calendar view.
                    self.current_start = start.toDate();
                    self.current_end = end.toDate();
                    self.dataset.read_slice(_.keys(self.fields), {
                        offset: 0,
                        domain: event_domain,
                        context: context,
                    }).done(function(events) {
                        // undo the read_slice if it the range has changed since it launched
                        if (self.current_start.getTime() != start.toDate().getTime() || self.current_end.getTime() != end.toDate().getTime()) {
                            self.dataset.ids = self.previous_ids;
                            return;
                        }
                        self.previous_ids = self.dataset.ids.slice();
                        if (self.dataset.index === null) {
                            if (events.length) {
                                self.dataset.index = 0;
                            }
                        } else if (self.dataset.index >= events.length) {
                            self.dataset.index = events.length ? 0 : null;
                        }
    
                        if (self.asset_event_source !== current_event_source) {
                            console.log("Consecutive ``do_search`` called. Cancelling.");
                            return;
                        }
    
                        if (!self.useContacts) {  // If we use all peoples displayed in the current month as filter in sidebars
                            var filter_item;
    
                            self.now_filter_ids = [];
    
                            var color_field = self.fields[self.color_field];
                            _.each(events, function (e) {
                                var key,val = null;
                                if (color_field.type == "selection") {
                                    key = e[self.color_field];
                                    val = _.find(color_field.selection, function(name){ return name[0] === key;});
                                } else {
                                    key = e[self.color_field][0];
                                    val = e[self.color_field];
                                }
                                if (!self.all_filters[key]) {
                                    filter_item = {
                                        value: key,
                                        label: val[1],
                                        color: self.get_color(key),
                                        avatar_model: (_.str.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                        is_checked: true
                                    };
                                    self.all_filters[key] = filter_item;
                                }
                                if (! _.contains(self.now_filter_ids, key)) {
                                    self.now_filter_ids.push(key);
                                }
                            });
    
                            if (self.sidebar) {
                                self.sidebar.filter.events_loaded();
                                self.sidebar.filter.set_filters();
    
                                events = $.map(events, function (e) {
                                    var key = color_field.type == "selection" ? e[self.color_field] : e[self.color_field][0];
                                    if (_.contains(self.now_filter_ids, key) &&  self.all_filters[key].is_checked) {
                                        return e;
                                    }
                                    return null;
                                });
                            }
    
                        }
                        var all_attendees = $.map(events, function (e) { return e[self.attendee_people]; });
                        all_attendees = _.chain(all_attendees).flatten().uniq().value();
    
                        self.all_attendees = {};
                        if (self.avatar_title !== null) {
                            new Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function(result) {
                                _.each(result, function(item) {
                                    self.all_attendees[item.id] = item.name;
                                });
                            }).done(function() {
                                return self.perform_necessary_name_gets(events).then(callback);
                            });
                        }
                        else {
                            _.each(all_attendees,function(item){
                                    self.all_attendees[item] = '';
                            });
                            return self.perform_necessary_name_gets(events).then(callback);
                        }
                    });
                },
                
                eventDataTransform: function (event) {
                    return self.event_data_transform(event);
                },
            };
            this.$calendar.fullCalendar('addEventSource', this.asset_event_source);
        },
        
    });
    
});