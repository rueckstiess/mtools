from datetime import MAXYEAR, datetime, timedelta

from dateutil.tz import tzutc

from .base_filter import BaseFilter
from mtools.util import OrderedDict
from mtools.util.hci import DateTimeBoundaries


def custom_parse_dt(value):
    return value


class DateTimeFilter(BaseFilter):
    """
    DateTimeFilter class.

    This filter has two parser arguments: --from and --to, both are
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
        ('--from', {'action': 'store', 'type': custom_parse_dt, 'nargs': '*',
                    'default': 'start',
                    'help': 'output starting at FROM', 'dest': 'from'}),
        ('--to', {'action': 'store', 'type': custom_parse_dt, 'nargs': '*',
                  'default': 'end', 'help': 'output up to TO', 'dest': 'to'})
        ]

    timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w',
                 'weeks', 'mo', 'months', 'y', 'years']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
              'Oct', 'Nov', 'Dec']

    dtRegexes = OrderedDict([
        # weekdays: see above
        ('weekday', r'|'.join(weekdays)),
        # month + day:  Jan 5, Oct 13, Sep 03, ...
        ('date', '(' + '|'.join(months) + ')' + r'\s+\d{1,2}'),
        ('word', r'now|start|end|today'),
        # 11:59, 1:13, 00:00, ...
        ('time2', r'\d{1,2}:\d{2,2}'),
        # 11:59:00, 1:13:12, 00:00:59, ...
        ('time3', r'\d{1,2}:\d{2,2}:\d{2,2}'),
        # offsets: +3min, -20s, +7days, ...
        ('offset', r'[\+-]\d+(' + '|'.join(timeunits) + ')'),
        ])

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        self.fromReached = False
        self.toReached = False

        self.active = (('from' in self.mlogfilter.args and
                        self.mlogfilter.args['from'] != 'start') or
                       ('to' in self.mlogfilter.args and
                        self.mlogfilter.args['to'] != 'end'))

    def setup(self):
        """Get start end end date of logfile before starting to parse."""
        if self.mlogfilter.is_stdin:
            # assume this year (we have no other info)
            now = datetime.now()
            self.startDateTime = datetime(now.year, 1, 1, tzinfo=tzutc())
            self.endDateTime = datetime(MAXYEAR, 12, 31, tzinfo=tzutc())

        else:
            logfiles = self.mlogfilter.args['logfile']
            self.startDateTime = min([lf.start +
                                      timedelta(hours=self
                                                .mlogfilter
                                                .args['timezone'][i])
                                      for i, lf in enumerate(logfiles)])
            self.endDateTime = max([lf.end +
                                    timedelta(hours=self
                                              .mlogfilter.args['timezone'][i])
                                    for i, lf in enumerate(logfiles)])

        # now parse for further changes to from and to datetimes
        dtbound = DateTimeBoundaries(self.startDateTime, self.endDateTime)
        self.fromDateTime, self.toDateTime = dtbound(self.mlogfilter
                                                     .args['from'] or None,
                                                     self.mlogfilter
                                                     .args['to'] or None)

        # define start_limit for mlogfilter's fast_forward method
        self.start_limit = self.fromDateTime

        # for single logfile, get file seek position of `to` datetime
        if (len(self.mlogfilter.args['logfile']) == 1 and not
                self.mlogfilter.is_stdin):

            if self.mlogfilter.args['to'] != "end":
                # fast forward, get seek value, then reset file
                logfile = self.mlogfilter.args['logfile'][0]
                logfile.fast_forward(self.toDateTime)
                self.seek_to = logfile.filehandle.tell()
                logfile.filehandle.seek(0)
            else:
                self.seek_to = -1
        else:
            self.seek_to = False

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        if self.fromReached and self.seek_to:
            if self.seek_to != -1:
                self.toReached = (self.mlogfilter.args['logfile'][0]
                                  .filehandle.tell() >= self.seek_to)
            return True
        else:
            # slow version has to check each datetime
            dt = logevent.datetime

            # if logevent has no datetime, accept if between --from and --to
            if dt is None:
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
        """
        Skip remaining lines.

        Overwrite BaseFilter.skipRemaining() and return True if all lines
        from here to the end of the file should be rejected (no output).
        """
        return self.toReached
