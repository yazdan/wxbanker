#!/usr/bin/env python
#
#    https://launchpad.net/wxbanker
#    analyzers.py: Copyright 2007-2009 Mike Rooney <mrooney@ubuntu.com>
#
#    This file is part of wxBanker.
#
#    wxBanker is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    wxBanker is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with wxBanker.  If not, see <http://www.gnu.org/licenses/>.

import datetime, calendar
from dateutil.relativedelta import relativedelta

class MonthlyAnalyzer:
    def __init__(self, months=12):
        self.Today = datetime.date.today()
        self.Months = months
        
    def GetDateRange(self):
        startMonth = self.Today - relativedelta(months=self.Months)
        start = datetime.date(startMonth.year, startMonth.month, 1)
        
        endMonth = self.Today - relativedelta(months=1)
        lastDay = calendar.monthrange(endMonth.year, endMonth.month)[1]
        end = datetime.date(endMonth.year, endMonth.month, lastDay)
        
        return start, end
    
    def GetEarnings(self, transactions):
        start, end = self.GetDateRange()
        buckets = {}
        def addtobucket(bucket, amount):
            if bucket in buckets: buckets[bucket] += amount
            else: buckets[bucket] = amount
                
        for t in sorted(transactions):
            date = t.Date
            if date >= start:
                if date > end:
                    break
                bucket = "%i.%s" % (date.year, str(date.month).zfill(2))
                addtobucket(bucket, t.Amount)
                
        return [(key, buckets[key]) for key in sorted(buckets)]
                
        