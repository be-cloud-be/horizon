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
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)

from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx

class PartnerXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, partners):
        # One sheet by partner
        sheet = workbook.add_worksheet('partners')
        i = 0
        sheet.write(i, 0, 'name')
        sheet.write(i, 1, 'firstname')
        sheet.write(i, 2, 'lastname')
        sheet.write(i, 3, 'initials')
        sheet.write(i, 4, 'reg_number')
        sheet.write(i, 5, 'mat_number')
        sheet.write(i, 6, 'student_current_bloc_name')
        sheet.write(i, 7, 'birthplace')
        sheet.write(i, 8, 'birthdate')
        i = 1
        for obj in partners:
            sheet.write(i, 0, obj.name)
            sheet.write(i, 1, obj.firstname)
            sheet.write(i, 2, obj.lastname)
            sheet.write(i, 3, obj.initials)
            sheet.write(i, 4, obj.reg_number)
            sheet.write(i, 5, obj.mat_number)
            sheet.write(i, 6, obj.student_current_bloc_name)
            sheet.write(i, 7, obj.birthplace)
            sheet.write(i, 8, obj.birthdate)
            i = i + 1

PartnerXlsx('report.res.partner.xlsx',
            'res.partner')