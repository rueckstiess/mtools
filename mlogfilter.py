#!/usr/bin/python

import argparse, re
from collections import OrderedDict
from datetime import date, time, datetime, timedelta, MINYEAR, MAXYEAR

class MongoDBLogParser:

    timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w', 'weeks', 'mo', 'months', 'y', 'years']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    timemark_regex = OrderedDict([         
        ('weekday', r'|'.join(weekdays)),                         # weekdays: see above
        ('date',    '('+ '|'.join(months) +')' + r'\s+\d{1,2}'),  # month + date:  Jan 5, Oct 13, Sep 03, ...
        ('word',    r'now|start|end|today|from'),
        ('time2',   r'\d{1,2}:\d{2,2}'),                          # 11:59, 1:13, 00:00, ...
        ('time3',   r'\d{1,2}:\d{2,2}:\d{2,2}'),                  # 11:59:00, 1:13:12, 00:00:59, ...
        ('offset',  r'[\+-]\d+(' + '|'.join(timeunits) + ')'),    # offsets: +3min, -20s, +7days, ...                    
        ])


    def __init__(self, args):
        self.args = args

        self.printing_out = False
        self.validate = {'date': False, 'tags':False, 'slow':False}

        if args['from'] != 'start' or args['to'] != 'end':
            self.dt_from = self.interpret_datetime(args['from'])
            self.dt_to = self.interpret_datetime(args['to'], self.dt_from)
            self.validate['date'] = True

        if args['tags']:
            self.tags = args['tags'].split()
            self.validate['tags'] = True

        if args['slow']:
            self.validate['slow'] = True


    def interpret_datetime(self, timemark, fromTime=None):
        dtdict = {}
        # go through all regexes in order and see which ones match
        for idx in self.timemark_regex:
            tmrx = self.timemark_regex[idx]
            mo = re.match('('+tmrx+')($|\s+)', timemark)
            if mo:
                dtdict[idx] = mo.group(0).rstrip()
                timemark = timemark[len(mo.group(0)):]

        if timemark:
            # still some string left after all filters applied. quitting.
            raise SystemExit("parsing error: don't understand '%s'" % timemark)


        skiptime = False
        notime = False
        nodate = False

        # current year
        now = datetime.now()
        dtdict['year'] = now.year

        # month and day
        if 'date' in dtdict:
            m, d = dtdict['date'].split()
            dtdict['month'] = self.months.index(m)+1
            dtdict['day'] = int(d)

            del dtdict['date']
            if 'weekday' in dtdict:
                # if we have fixed date, we don't need the weekday
                del dtdict['weekday']

        elif 'weekday' in dtdict:
            # assume most-recently occured weekday
            today = date.today()
            offset = (today.weekday() - self.weekdays.index(dtdict['weekday'])) % 7
            d = today - timedelta(days=offset)
            dtdict['month'] = d.month
            dtdict['day'] = d.day
            
            del dtdict['weekday']

        elif 'word' in dtdict:
            # handle special case of now, start, end
            if dtdict['word'] == 'now':
                dtdict['month'], dtdict['day'] = now.month, now.day
                dtdict['hour'], dtdict['minute'], dtdict['second'] = now.hour, now.minute, now.second
                skiptime = True
            elif dtdict['word'] == 'today':
                dtdict['month'], dtdict['day'] = now.month, now.day            
            elif dtdict['word'] == 'start':
                dtdict['year'], dtdict['month'], dtdict['day'] = MINYEAR, 1 , 1
                skiptime = True
            elif dtdict['word'] == 'end':
                dtdict['year'], dtdict['month'], dtdict['day'] = MAXYEAR, 12, 31
                skiptime = True

            del dtdict['word']

        elif 'time2' in dtdict or 'time3' in dtdict:
            # just time given, use today
            dtdict['month'], dtdict['day'] = now.month, now.day

        else:
            # nothing given, use same as start
            dtdict['year'], dtdict['month'], dtdict['day'] = MINYEAR, 1 , 1
            nodate = True


        if not skiptime:
            if 'time2' in dtdict:
                h, m = dtdict['time2'].split(':')
                dtdict['hour'] = int(h)
                dtdict['minute'] = int(m)
                dtdict['second'] = 0
                del dtdict['time2']

            elif 'time3' in dtdict:
                h, m, s = dtdict['time3'].split(':')
                dtdict['hour'] = int(h)
                dtdict['minute'] = int(m)
                dtdict['second'] = int(s)
                del dtdict['time3']

            else:
                dtdict['hour'] = dtdict['minute'] = dtdict['second'] = 0
                notime = True

        
        if 'offset' in dtdict:

            if notime and nodate and fromTime != None:
                dtdict['year'], dtdict['month'], dtdict['day'] = fromTime.year, fromTime.month, fromTime.day
                dtdict['hour'], dtdict['minute'], dtdict['second'] = fromTime.hour, fromTime.minute, fromTime.second

            offset = dtdict['offset']
            del dtdict['offset']

            # create datetime object
            dt = datetime(**dtdict)
        
            matches = re.match(r'([+-])(\d+)([a-z]+)', offset)
            operator, value, unit = matches.groups()
            
            if unit in ['s', 'sec']:
                unit = 'seconds'
            elif unit in ['m', 'min']:
                unit = 'minutes'
            elif unit in ['h', 'hours']:
                unit = 'hours'
            elif unit in ['d', 'days']:
                unit = 'days'
            elif unit in ['w', 'weeks']:
                unit = 'weeks'
            elif unit in ['m', 'months']:
                unit = 'months'
            elif unit in ['y', 'years']:
                unit = 'years'

            mult = 1
            if operator == '-':
                mult = -1

            dt = dt + eval('timedelta(%s=%i)'%(unit, mult*int(value)))
        
        else:
            dt = datetime(**dtdict)


        return dt    


    def check_date(self, line):
        if not self.validate['date']:
            return True

        if line.startswith('***'):
            # line starts with stars, output
            return self.printing_out

        tokens = line.split()
        if len(tokens) < 4:
            # if there aren't enough tokens for date+time, output line
            return self.printing_out

        _, month, day, time = tokens[:4]
        
        # check if it actually is a date+time
        if not (month in self.months and
                re.match(r'\d{1,2}', day) and
                re.match(r'\d{2}:\d{2}:\d{2}', time)):
            return self.printing_out

        month = self.months.index(month)+1
        h, m, s = time.split(':')
        year = datetime.now().year

        dt = datetime(int(year), int(month), int(day), int(h), int(m), int(s))
        if self.dt_from <= dt <= self.dt_to:
            self.printing_out = True
            return True
        elif dt > self.dt_to:
            self.printing_out = False
            return False


    def check_tags(self, line):
        if not self.validate['tags']:
            return True

        for tag in self.tags:
            if re.search(tag, line):
                return True
        return False


    def check_slow(self, line):
        if not self.validate['slow']:
            return True

        return re.search(r'\d{4,}ms', line)


    def parse(self):
        f = open(self.args['logfile'], 'r')
        
        for i, line in enumerate(f):
            if self.check_tags(line) and \
               self.check_date(line) and \
               self.check_slow(line):
                print line,



def array_to_string(arr):
    if isinstance(arr, list):
        return " ".join(arr)
    else:
        return arr



if __name__ == '__main__':
      
    parser = argparse.ArgumentParser(description='mongod/mongos log file parser.')

    parser.add_argument('logfile', action='store', help='logfile to parse')
    parser.add_argument('--from', action='store', nargs='*', default='start', help='output starting at FROM', dest='from')
    parser.add_argument('--to', action='store', nargs='*', default='end', help='output up to TO', dest='to')
    parser.add_argument('--tags', action='store', nargs='*', help='only output lines matching any of [TAG]')
    parser.add_argument('--slow', action='store_true', help='only output lines with query times longer than 1000 ms')

    args = vars(parser.parse_args())
    args = dict((k, array_to_string(args[k])) for k in args)

    mdblogparser = MongoDBLogParser(args)
    mdblogparser.parse()



        





    
