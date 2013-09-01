from mtools.util import OrderedDict
from mtools.util.hci import DateTimeBoundaries
from datetime import datetime, timedelta, MINYEAR, MAXYEAR
from mtools.util.logline import LogLine
from mtools.util.logfile import LogFile
from math import ceil 

from base_filter import BaseFilter


def custom_parse_dt(value):
    return value


class DateTimeFilter(BaseFilter):
    """ This filter has two parser arguments: --from and --to, both are 
        optional. All possible values for --from and --to can be described as:

        [DATE] [TIME] [OFFSET] in that order, separated by a space.

        [DATE] can be any of
            - a 3-letter weekday (Mon, Tue, Wed, ...)
            - a date as 3-letter month, 1-2 digits day (Sep 5, Jan 31, Aug 08)
            - the words: today, now, start, end

        [TIME] can be any of
            - hours and minutes (20:15, 04:00, 3:00)
            - hours, minutes and seconds (13:30:01, 4:55:55)

        [OFFSET] consists of [OPERATOR][VALUE][UNIT]   (no spaces in between)

        [OPERATOR] can be + or - (note that - can only be used if the whole 
            "[DATE] [TIME] [OFFSET]" is in quotation marks, otherwise it would 
            be confused with a separate parameter)

        [VALUE] can be any number

        [UNIT] can be any of s, sec, m, min, h, hours, d, days, w, weeks, mo,
            months, y, years

        The [OFFSET] is added/subtracted to/from the specified [DATE] [TIME].

        For the --from parameter, the default is the same as 'start' 
            (0001-01-01 00:00:00). If _only_ an [OFFSET] is given, it is 
            added to 'start' (which is not very useful).

        For the --to parameter, the default is the same as 'end' 
            (9999-31-12 23:59:59). If _only_ an [OFFSET] is given, however, 
            it is added to [FROM].

        Examples:  
            --from Sun 10:00 
                goes from last Sunday 10:00:00am to the end of the file

            --from Sep 29
                goes from Sep 29 00:00:00 to the end of the file

            --to today 15:00
                goes from the beginning of the file to today at 15:00:00

            --from today --to +1h
                goes from today's date 00:00:00 to today's date 01:00:00

            --from 20:15 --to +3m  
                goes from today's date at 20:15:00 to today's date at 20:18:00
    """

    filterArgs = [
       ('--from', {'action':'store',  'type':custom_parse_dt, 'nargs':'*', 'default':'start', 'help':'output starting at FROM', 'dest':'from'}), 
       ('--to',   {'action':'store',  'type':custom_parse_dt, 'nargs':'*', 'default':'end',   'help':'output up to TO',         'dest':'to'})
    ]

    timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w', 'weeks', 'mo', 'months', 'y', 'years']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    dtRegexes = OrderedDict([         
        ('weekday', r'|'.join(weekdays)),                         # weekdays: see above
        ('date',    '('+ '|'.join(months) +')' + r'\s+\d{1,2}'),  # month + day:  Jan 5, Oct 13, Sep 03, ...
        ('word',    r'now|start|end|today'),
        ('time2',   r'\d{1,2}:\d{2,2}'),                          # 11:59, 1:13, 00:00, ...
        ('time3',   r'\d{1,2}:\d{2,2}:\d{2,2}'),                  # 11:59:00, 1:13:12, 00:00:59, ...
        ('offset',  r'[\+-]\d+(' + '|'.join(timeunits) + ')'),    # offsets: +3min, -20s, +7days, ...                    
    ])

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        self.fromReached = False
        self.toReached = False

        if 'from' in self.mlogfilter.args or 'to' in self.mlogfilter.args:
            self.active = True


    def setup(self):
        """ get start end end date of logfile before starting to parse. """

        if self.mlogfilter.is_stdin:
            # assume this year (we have no other info)
            now = datetime.now()
            self.startDateTime = datetime(now.year, 1, 1)
            self.endDateTime = datetime(MAXYEAR, 12, 31)
        
        else:
            logfiles = [LogFile(lf) for lf in self.mlogfilter.args['logfile']]
            self.startDateTime = min([lf.start+timedelta(hours=self.mlogfilter.args['timezone'][i]) for i, lf in enumerate(logfiles)])
            self.endDateTime = max([lf.end+timedelta(hours=self.mlogfilter.args['timezone'][i]) for i, lf in enumerate(logfiles)])

        # now parse for further changes to from and to datetimes
        dtbound = DateTimeBoundaries(self.startDateTime, self.endDateTime)
        self.fromDateTime, self.toDateTime = dtbound(self.mlogfilter.args['from'] or None, 
                                                     self.mlogfilter.args['to'] or None)

    def accept(self, logline):
        dt = logline.datetime

        # if logline has no datetime, accept if between --from and --to
        if dt == None:
            return self.fromReached

        if self.fromDateTime <= dt <= self.toDateTime:
            self.toReached = False
            self.fromReached = True
            return True

        elif dt > self.toDateTime:
            self.toReached = True
            return False

        else: 
            return False

        
    def skipRemaining(self):
        return self.toReached


    def _find_curr_line(self, logfile, prev=False):
        curr_pos = logfile.tell()

        logfile.seek(curr_pos, 0)
        line = None

        # jump back 15k characters (at most) and find last newline char
        jump_back = min(logfile.tell(), 15000)
        logfile.seek(-jump_back, 1)
        buff = logfile.read(jump_back)
        logfile.seek(curr_pos, 0)

        newline_pos = buff.rfind('\n')
        if prev:
            newline_pos = buff[:newline_pos].rfind('\n')

        # move back to last newline char
        logfile.seek(newline_pos - jump_back, 1)

        while line != '':
            line = logfile.readline()
            logline = LogLine(line)
            date = logline.datetime
            if date:
                return logline

        return None

    def seek_binary(self):
        for logfile in self.mlogfilter.args['logfile']: 
            logfile_info = LogFile(logfile)

            min_mark = 0
            max_mark = logfile_info.filesize
            step_size = max_mark

            ll = None
            if self.fromDateTime:

                # search for lower bound
                while abs(step_size) > 100:
                    step_size = ceil(step_size / 2.)
                    
                    logfile.seek(step_size, 1)
                    ll = self._find_curr_line(logfile)
                    if not ll:
                        break
                                    
                    if ll.datetime >= self.fromDateTime:
                        step_size = -abs(step_size)
                    else:
                        step_size = abs(step_size)


                # now walk backwards until we found a truely smaller line
                while logfile.tell() >= 2 and ll.datetime >= self.fromDateTime:
                    logfile.seek(-2, 1)
                    ll = self._find_curr_line(logfile, prev=True)

