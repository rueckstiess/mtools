from mtools.util import OrderedDict
from datetime import date, time, datetime, timedelta
import re
import copy
from dateutil import parser
from dateutil.tz import tzutc

class DateTimeBoundaries(object):

    timeunits = ['secs', 'sec', 's', 'mins', 'min', 'm', 'months', 'month', 'mo', 'hours', 'hour', 'h', 'days', 'day', 'd', 'weeks','week', 'w', 'years', 'year', 'y']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    dtRegexes = OrderedDict([ 
        # special constants
        ('constant', re.compile('(now|start|end|today|yesterday)' + '($|\s+)')),                        
        # weekday: Mon, Wed, Sat
        ('weekday',  re.compile('(' + '|'.join(weekdays) + ')' + '($|\s+)')),                 
        # 11:59:00.123, 1:13:12.004  (also match timezone postfix like Z or +0700 or -05:30)
        ('time',     re.compile('(?P<hour>\d{1,2}):(?P<minute>\d{2,2})' + '(?::(?P<second>\d{2,2})(?:.(?P<microsecond>\d{3,3}))?)?([0-9Z:\+\-]+)?' + '($|\s+)')),                                      
        # offsets: +3min, -20s, +7days  (see timeunits above)
        ('offset',   re.compile('(?P<operator>[\+-])(?P<value>\d+)(?P<unit>' + '|'.join(timeunits) +')'+'($|\s+)'))                          
    ])

    def __init__(self, start, end):
        """ initialize the DateTimeBoundaries object with true start and end datetime objects. """

        if start > end:
            raise ValueError('Error in DateTimeBoundaries: end cannot be before start datetime.')

        # make sure all datetimes are timezone-aware
        self.start = start
        if not self.start.tzinfo:
            self.start = self.start.replace(tzinfo=tzutc())
        
        self.end = end
        if not self.end.tzinfo:
            self.end = self.end.replace(tzinfo=tzutc())


    def string2dt(self, s, lower_bound=None):
        original_s = s
        
        result = {}
        dt = None

        # if s is completely empty, return start or end, depending on what parameter is evaluated
        if s == '':
            return self.end if lower_bound else self.start

        # first try to match the defined regexes
        for idx in self.dtRegexes:
            regex = self.dtRegexes[idx]
            mo = regex.search(s)
            # if match was found, cut it out of original string and store in result
            if mo:
                result[idx] = mo
                s = s[:mo.start(0)] + s[mo.end(0):]

        # handle constants
        if 'constant' in result:
            constant = result['constant'].group(0).strip()
            if constant == 'end':
                dt = self.end
            elif constant == 'start':
                dt = self.start
            elif constant == 'today':
                dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzutc())
            elif constant == 'yesterday':
                dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzutc()) - timedelta(days=1)
            elif constant == 'now':
                dt = datetime.now().replace(tzinfo=tzutc())

        elif 'weekday' in result:
                weekday = result['weekday'].group(0).strip()
                # assume most-recently occured weekday in logfile
                most_recent_date = self.end.replace(hour=0, minute=0, second=0, microsecond=0)
                offset = (most_recent_date.weekday() - self.weekdays.index(weekday)) % 7
                dt = most_recent_date - timedelta(days=offset)
            
        # if anything remains unmatched, try parsing it with dateutil's parser
        if s.strip() != '':
            try:
                if dt:
                    dt = parser.parse(s, default=dt, tzinfos=tzutc)
                else:
                    dt = parser.parse(s, default=datetime(self.end.year, 1, 1, tzinfo=tzutc()), tzinfos=tzutc)
            except ValueError as e:
                raise ValueError("Error in DateTimeBoundaries: can't parse datetime from %s" % s)

        if not dt:
            dt = lower_bound or self.end
        
        # time is applied separately (not through the parser) so that string containing only time don't use today as default date (parser behavior)
        if 'time' in result:
            dct = dict( (k, int(v)) for k,v in result['time'].groupdict(0).iteritems() )
            dct['microsecond'] *= 1000
            dt = dt.replace(**dct)

        # apply offset
        if 'offset' in result:

            # separate in operator, value, unit
            dct = result['offset'].groupdict()

            mult = 1
            if dct['unit'] in ['s', 'sec', 'secs']:
                dct['unit'] = 'seconds'
            elif dct['unit'] in ['m', 'min', 'mins']:
                dct['unit'] = 'minutes'
            elif dct['unit'] in ['h', 'hour', 'hours']:
                dct['unit'] = 'hours'
            elif dct['unit'] in ['d', 'day', 'days']:
                dct['unit'] = 'days'
            elif dct['unit'] in ['w', 'week', 'weeks']:
                dct['unit'] = 'days'
                mult = 7
            elif dct['unit'] in ['mo', 'month', 'months']:
                dct['unit'] = 'days'
                mult = 30.43
            elif dct['unit'] in ['y', 'year', 'years']:
                dct['unit'] = 'days'
                mult = 365.24
            
            if dct['operator'] == '-':
                mult *= -1

            dt = dt + eval('timedelta(%s=%i)'%(dct['unit'], mult*int(dct['value'])))

        # if parsed datetime is out of bounds and no year specified, try to adjust year
        year_present = re.search('\d{4,4}', original_s)

        if not year_present:
            if dt < self.start and dt.replace(year=dt.year+1) >= self.start and dt.replace(year=dt.year+1) <= self.end:
                dt = dt.replace(year=dt.year+1)
            elif dt > self.end and dt.replace(year=dt.year-1) >= self.start and dt.replace(year=dt.year-1) <= self.end:
                dt = dt.replace(year=dt.year-1)

        return dt


    def __call__(self, from_str=None, to_str=None):
        """ sets the boundaries based on `from` and `to` strings. """

        from_dt = self.string2dt(from_str, lower_bound=None)
        to_dt = self.string2dt(to_str, lower_bound=from_dt)

        if to_dt < from_dt:
            raise ValueError('Error in DateTimeBoundaries: lower bound is greater than upper bound.')

        # limit from and to at the real boundaries
        if to_dt > self.end:
            to_dt = self.end
        
        if from_dt < self.start:
            from_dt = self.start

        return from_dt, to_dt


if __name__ == '__main__':
    
    dtb = DateTimeBoundaries(parser.parse('June 15 2013 13:00 UTC'), parser.parse('Jan 10 2014 16:21 UTC'))
    # lower, upper = dtb('Jan 13 -5d', 'Jan 15 -1h')
    # print lower
    # print upper

    print dtb.string2dt("start +3h")

