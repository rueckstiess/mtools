from mtools.util import OrderedDict
from datetime import date, time, datetime, timedelta
import re
import copy
from dateutil import parser

class DateTimeBoundaries(object):

    timeunits = ['secs', 'sec', 's', 'mins', 'min', 'm', 'months', 'month', 'mo', 'hours', 'hour', 'h', 'days', 'day', 'd', 'weeks','week', 'w', 'years', 'year', 'y']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    dtRegexes = OrderedDict([ 
        ('year',     re.compile('(\d{4,})' + '($|\s+)')),                                     # year: 2005, 1993        
        ('monthday', re.compile('(' + '|'.join(months) + ')' + '\s+\d{1,2}' + '($|\s+)')),    # month + day:  Jan 5, Sep 03
        ('month',    re.compile('(' + '|'.join(months) + ')' + '($|\s+)')),                   # month alone:  Feb, Apr, Dec
        ('constant', re.compile('(now|start|end|today)' + '($|\s+)')),                        # special constants
        ('weekday',  re.compile('(' + '|'.join(weekdays) + ')' + '($|\s+)')),                 # weekday: Mon, Wed, Sat
        ('time4',    re.compile('(\d{1,2}:\d{2,2}:\d{2,2}.\d{3,})' + '($|\s+)')),             # 11:59:00.123, 1:13:12.004
        ('time3',    re.compile('(\d{1,2}:\d{2,2}:\d{2,2})' + '($|\s+)')),                    # 11:59:00, 1:13:12, 00:00:59
        ('time2',    re.compile('(\d{1,2}:\d{2,2})' + '($|\s+)')),                            # 11:59, 1:13, 00:00
        ('offset',   re.compile('([\+-]\d+(' + '|'.join(timeunits) +'))'+'($|\s+)')),         # offsets: +3min, -20s, +7days                
    ])

    def __init__(self, start, end):
        """ initialize the DateTimeBoundaries object with true start and end datetime objects. """
        self.start = start
        self.end = end


    def extract_regex(self, timemark):
        
        timemark_original = timemark
        dtdict = {}
        matched = False

        # go through all regexes in order and see which ones match
        while timemark:
            matched = False
            for idx in self.dtRegexes:
                regex = self.dtRegexes[idx]
                mo = regex.match(timemark)
                if mo:
                    dtdict[idx] = mo.group(0).rstrip()
                    timemark = timemark[len(mo.group(0)):]
                    matched = True
                    break
            if not matched:
                break

        if timemark:
            try:
                dt = parser.parse(timemark_original)
                dtdict['parsed'] = dt

            except TypeError:
                # still some string left after all filters applied. quitting.
                raise ValueError("can't parse '%s'" % timemark)

        return dtdict

    
    def parse_dt(self, dtdict, from_dt=None):
        
        skiptime = False
        notime = False
        nodate = False

        now = datetime.now()

        # check if dateutil parser was used, return dt immediately
        if 'parsed' in dtdict:
            return dtdict['parsed']

        # process year
        if 'year' in dtdict:
            dtdict['year'] = int(dtdict['year'])
        else:
            dtdict['year'] = self.start.year

        # process month and day
        if 'monthday' in dtdict:
            m, d = dtdict['monthday'].split()
            dtdict['month'] = self.months.index(m)+1
            dtdict['day'] = int(d)

            del dtdict['monthday']
            if 'weekday' in dtdict:
                # if we have fixed date, we don't need the weekday
                del dtdict['weekday']

        elif 'weekday' in dtdict:
            # assume most-recently occured weekday in logfile
            most_recent_date = self.end.date()
            offset = (most_recent_date.weekday() - self.weekdays.index(dtdict['weekday'])) % 7
            d = most_recent_date - timedelta(days=offset)
            dtdict['month'] = d.month
            dtdict['day'] = d.day
            
            del dtdict['weekday']

        elif 'month' in dtdict:
            m = dtdict['month']
            dtdict['month'] = self.months.index(m)+1
            dtdict['day'] = 1

        elif 'constant' in dtdict:
            # handle special case of now, start, end
            if dtdict['constant'] == 'now':
                dtdict['year'], dtdict['month'], dtdict['day'] = now.year, now.month, now.day
                dtdict['hour'], dtdict['minute'], dtdict['second'] = now.hour, now.minute, now.second
                skiptime = True
            elif dtdict['constant'] == 'today':
                dtdict['year'], dtdict['month'], dtdict['day'] = now.year, now.month, now.day               
            elif dtdict['constant'] == 'start':
                dtdict['year'], dtdict['month'], dtdict['day'] = self.start.year, self.start.month, self.start.day
                dtdict['hour'], dtdict['minute'], dtdict['second'] = self.start.hour, self.start.minute, self.start.second 
                skiptime = True
            elif dtdict['constant'] == 'end':
                dtdict['year'], dtdict['month'], dtdict['day'] = self.end.year, self.end.month, self.end.day
                dtdict['hour'], dtdict['minute'], dtdict['second'] = self.end.hour, self.end.minute, self.end.second 
                skiptime = True

            del dtdict['constant']

        elif 'time2' in dtdict or 'time3' in dtdict or 'time4' in dtdict:
            # just time given, use today
            dtdict['year'], dtdict['month'], dtdict['day'] = self.end.year, self.end.month, self.end.day

        else:
            # nothing given, use same as start
            dtdict['year'], dtdict['month'], dtdict['day'] = self.start.year, self.start.month, self.start.day
            nodate = True

        # process time
        if not skiptime:
            if 'time2' in dtdict:
                h, m = dtdict['time2'].split(':')
                dtdict['hour'] = int(h)
                dtdict['minute'] = int(m)
                del dtdict['time2']

            elif 'time3' in dtdict:
                h, m, s = dtdict['time3'].split(':')
                dtdict['hour'] = int(h)
                dtdict['minute'] = int(m)
                dtdict['second'] = int(s)
                del dtdict['time3']

            elif 'time4' in dtdict:
                hms, us = dtdict['time4'].split('.')
                h, m, s = hms.split(':')
                dtdict['hour'] = int(h)
                dtdict['minute'] = int(m)
                dtdict['second'] = int(s)
                dtdict['microsecond'] = int(us) * 1000
                del dtdict['time4']

            else:
                notime = True

        # process offset
        if 'offset' in dtdict:

            offset = dtdict['offset']
            del dtdict['offset']

            matches = re.match(r'([+-])(\d+)([a-z]+)', offset)
            operator, value, unit = matches.groups()

            if notime and nodate:
                if from_dt:  
                    dtdict['year'], dtdict['month'], dtdict['day'] = from_dt.year, from_dt.month, from_dt.day
                    dtdict['hour'], dtdict['minute'], dtdict['second'] = from_dt.hour, from_dt.minute, from_dt.second
                else:
                    if operator == '+':
                        dtdict['year'], dtdict['month'], dtdict['day'] = self.start.year, self.start.month, self.start.day
                        dtdict['hour'], dtdict['minute'], dtdict['second'] = self.start.hour, self.start.minute, self.start.second
                    else:
                        dtdict['year'], dtdict['month'], dtdict['day'] = self.end.year, self.end.month, self.end.day
                        dtdict['hour'], dtdict['minute'], dtdict['second'] = self.end.hour, self.end.minute, self.end.second          

            # create datetime object
            dt = datetime(**dtdict)
            
            mult = 1

            if unit in ['s', 'sec', 'secs']:
                unit = 'seconds'
            elif unit in ['m', 'min', 'mins']:
                unit = 'minutes'
            elif unit in ['h', 'hour', 'hours']:
                unit = 'hours'
            elif unit in ['d', 'day', 'days']:
                unit = 'days'
            elif unit in ['w', 'week', 'weeks']:
                unit = 'days'
                mult = 7
            elif unit in ['mo', 'month', 'months']:
                unit = 'days'
                mult = 30.43
            elif unit in ['y', 'year', 'years']:
                unit = 'days'
                mult = 365.24
            
            if operator == '-':
                mult *= -1

            dt = dt + eval('timedelta(%s=%i)'%(unit, mult*int(value)))
        
        else:
            dt = datetime(**dtdict)

        if dt < self.start:
            dt = self.start

        if dt > self.end:
            dt = self.end

        return dt  


    def __call__(self, from_dt=None, to_dt=None):
        """ sets the boundaries based on `from` and `to` strings. """

        dtdict = self.extract_regex(from_dt)
        if from_dt:
            from_dt = self.parse_dt(dtdict)
        else: 
            from_dt = self.start

        dtdict = self.extract_regex(to_dt)
        if to_dt:
            to_dt = self.parse_dt(dtdict, from_dt)
        else:
            to_dt = self.end
    
        return from_dt, to_dt


if __name__ == '__main__':
    start = datetime(2012, 10, 14)
    end = datetime(2013, 6, 2)
    dtb = DateTimeBoundaries(start, end)
    print dtb('Feb 19', '+1day')



