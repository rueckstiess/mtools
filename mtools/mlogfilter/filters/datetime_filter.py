from mtools.util import OrderedDict
from mtools.util.hci import DateTimeBoundaries
from datetime import datetime, MINYEAR, MAXYEAR
from mtools.util.logline import LogLine

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

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        self.fromReached = False
        self.toReached = False

        if 'from' in self.commandLineArgs or 'to' in self.commandLineArgs:
            self.active = True


    def setup(self):
        """ get start end end date of logfile before starting to parse. """
        logfile = self.commandLineArgs['logfile']
        seekable = False

        if logfile:
            seekable = logfile.name != "<stdin>"

        if not seekable:
            # assume this year (we have no other info)
            now = datetime.now()
            self.startDateTime = datetime(now.year, 1, 1)
            self.endDateTime = datetime(MAXYEAR, 12, 31)
            # self.fromDateTime = datetime(MINYEAR, 1, 1)
            # self.toDateTime = datetime(MAXYEAR, 12, 31)
        
        else:
            # get start datetime 
            for line in logfile:
                logline = LogLine(line)
                date = logline.datetime
                if date:
                    break
            self.startDateTime = date

            # get end datetime (lines are at most 10k, go back 15k at most to make sure)
            logfile.seek(0, 2)
            file_size = logfile.tell()
            logfile.seek(-min(file_size, 15000), 2)

            for line in reversed(logfile.readlines()):
                logline = LogLine(line)
                date = logline.datetime
                if date:
                    break
            self.endDateTime = date

            # if there was a roll-over, subtract 1 year from start time
            if self.endDateTime < self.startDateTime:
                self.startDateTime = self.startDateTime.replace(year=self.startDateTime.year-1)

            # reset logfile
            logfile.seek(0)

        # now parse for further changes to from and to datetimes
        dtbound = DateTimeBoundaries(self.startDateTime, self.endDateTime)
        self.fromDateTime, self.toDateTime = dtbound(self.commandLineArgs['from'] or None, 
                                                     self.commandLineArgs['to'] or None)

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


