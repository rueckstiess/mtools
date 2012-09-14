import argparse, re
from collections import OrderedDict
from datetime import date, time, datetime, timedelta, MINYEAR, MAXYEAR

parser = argparse.ArgumentParser(description='mongod/mongos log file parser.')

parser.add_argument('logfile', action='store', help='logfile to parse')
parser.add_argument('-f', '--from', action='store', nargs='*', default='start', help='print output starting at FROM', dest='from')
parser.add_argument('-t', '--to', action='store', nargs='*', default='end', help='print output up to TO', dest='to')

timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w', 'weeks', 'mo', 'months', 'y', 'years']
weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

timemark_regex = OrderedDict([         
('weekday', r'|'.join(weekdays)),                       # weekdays: see above
('date',    '('+ '|'.join(months) +')' + r'\s+\d{1,2}'),                # month + date:  Jan 5, Oct 13, Sep 03, ...
('time2',   r'\d{1,2}:\d{2,2}'),                        # 11:59, 1:13, 00:00, ...
('time3',   r'\d{1,2}:\d{2,2}:\d{2,2}'),                # 11:59:00, 1:13:12, 00:00:59, ...
('word',    r'now|start|end'),
('offset',  r'[\+-]\d+(' + '|'.join(timeunits) + ')'),  # offsets: +3min, -20s, +7days, ...                    
])

def array_to_string(arr):
    if isinstance(arr, list):
        return " ".join(arr)
    else:
        return arr

def validate_timemark(timemark):
    dtdict = {}
    # go through all regexes in order and see which ones match
    for idx in timemark_regex:
        tmrx = timemark_regex[idx]
        mo = re.match('('+tmrx+')($|\s+)', timemark)
        if mo:
            dtdict[idx] = mo.group(0).rstrip()
            timemark = timemark[len(mo.group(0)):]

    if timemark:
        raise SystemExit("parsing error: don't understand '%s'" % timemark)

    # current year
    now = datetime.now()
    dtdict['year'] = now.year

    # month and day
    if 'date' in dtdict:
        dtdict['month'], dtdict['day'] = dtdict['date'].split(' ')
        dtdict['day'] = int(dtdict['day'])

        del dtdict['date']

    elif 'weekday' in dtdict:
        # assume most-recently occured weekday
        today = date.today()
        offset = (today.weekday() - weekdays.index(dtdict['weekday'])) % 7
        d = today - timedelta(days=offset)
        dtdict['month'] = months[d.month-1]
        dtdict['day'] = d.day
        del dtdict['weekday']

    elif 'word' in dtdict:
        # handle special case of now, start, end
        if dtdict['word'] == 'now':
            dtdict['month'], dtdict['day'] = months[now.month-1], now.day
        elif dtdict['word'] == 'start':
            dtdict['year'], dtdict['month'], dtdict['day'] = MINYEAR, 'Jan', 1
        elif dtdict['word'] == 'end':
            dtdict['year'], dtdict['month'], dtdict['day'] = MAXYEAR, 'Dec', 31

        del dtdict['word']

    else:
        dtdict['month'], dtdict['day']  = months[now.month-1], now.day

    dtdict['weekday'] = weekdays[date(now.year, months.index(dtdict['month'])+1, dtdict['day']).weekday()]

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

    return dtdict     



if __name__ == '__main__':
        
    args = vars(parser.parse_args())
    args = dict((k, array_to_string(args[k])) for k in args)

    print
    print validate_timemark(args['from'])
    print validate_timemark(args['to'])
