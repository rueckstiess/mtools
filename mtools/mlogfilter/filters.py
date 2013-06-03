from mtools.util import OrderedDict
from mtools.util.logline import LogLine
from datetime import date, time, datetime, timedelta, MINYEAR, MAXYEAR
import re

class BaseFilter:
    """ Base Filter class. All filters need to derive from it and implement
        their version of filterArgs, accept, and optionally skipRemaining.

        filterArgs needs to be a list of tuples with 2 elements each. The 
        first tuple element is the filter argument, e.g. --xyz. The second
        element of the tuple is a dictionary that gets passed to the 
        ArgumentParser object's add_argument method.
    """

    filterArgs = []

    def __init__(self, commandLineArgs):
        """ constructor. save command line arguments and set active to False
            by default. 
        """
        self.commandLineArgs = commandLineArgs

        # filters need to actively set this flag to true
        self.active = False

    def accept(self, logline):
        """ overwrite this method in subclass and return True if the provided 
            logline should be accepted (causing output), or False if not.
        """
        return True

    def skipRemaining(self):
        """ overwrite this method in sublcass and return True if all lines
            from here to the end of the file should be rejected (no output).
        """
        return False



class WordFilter(BaseFilter):
    """ accepts only if line contains any of the words specified by --word 
    """

    filterArgs = [
        ('--word', {'action':'store', 'nargs':'*', 'help':'only output lines matching any of WORD'}),
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)

        # extract all arguments passed into 'word'
        if 'word' in self.commandLineArgs and self.commandLineArgs['word']:
            self.words = self.commandLineArgs['word'].split()
            self.active = True
        else:
            self.active = False

    def accept(self, logline):
        for word in self.words:
            if re.search(word, logline.line_str):
                return True
        return False



class LogLineFilter(BaseFilter):
    """ 
    """
    filterArgs = [
        ('--namespace', {'action':'store', 'metavar':'NS', 'help':'only output log lines matching operations on NS.'}),
        ('--operation', {'action':'store', 'metavar':'OP', 'help':'only output log lines matching operations of type OP.'}),
        ('--thread', {'action':'store', 'help':'only output log lines of thread THREAD.'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)

        self.namespace = None
        self.operation = None
        self.thread = None

        if 'namespace' in self.commandLineArgs and self.commandLineArgs['namespace']:
            self.namespace = self.commandLineArgs['namespace']
            self.active = True
        if 'operation' in self.commandLineArgs and self.commandLineArgs['operation']:
            self.operation = self.commandLineArgs['operation']
            self.active = True
        if 'thread' in self.commandLineArgs and self.commandLineArgs['thread']:
            self.thread = self.commandLineArgs['thread']
            self.active = True

    def accept(self, logline):
        if self.namespace and logline.namespace == self.namespace:
            return True
        if self.operation and logline.operation == self.operation:
            return True
        if self.thread and logline.thread == self.thread:
            return True

        return False



class SlowFilter(BaseFilter):
    """ accepts only lines that have a duration that is longer than the specified 
        parameter in ms (default 1000).
    """
    filterArgs = [
        ('--slow', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times longer than SLOW ms (default 1000)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'slow' in self.commandLineArgs and self.commandLineArgs['slow'] != False:
            self.active = True
            if self.commandLineArgs['slow'] == None:
                self.slowms = 1000
            else:
                self.slowms = self.commandLineArgs['slow']

    def accept(self, logline):
        if logline.duration:
            return logline.duration >= self.slowms
        return False


class FastFilter(BaseFilter):
    """ accepts only lines that have a duration that is shorter than the specified
        parameter in ms.
    """
    filterArgs = [
        ('--fast', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times shorter than FAST ms (default 1000)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'fast' in self.commandLineArgs and self.commandLineArgs['fast'] != False:
            self.active = True
            if self.commandLineArgs['fast'] == None:
                self.fastms = 1000
            else:
                self.fastms = self.commandLineArgs['fast']

    def accept(self, logline):
        if self.active and logline.duration:
            return logline.duration <= self.fastms
        return False


class TableScanFilter(BaseFilter):
    """ accepts only if the line contains a nscanned:[0-9] nreturned:[0-9] where the ratio of nscanned:nreturned is > 100 and nscanned > 10000
    """
    filterArgs = [
        ('--scan', {'action':'store_true', 'help':'only output lines which appear to be table scans (if nscanned>10000 and ratio of nscanned to nreturned>100)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'scan' in self.commandLineArgs:
            self.active = self.commandLineArgs['scan']

    def accept(self, logline):

        ns = logline.nscanned
        nr = logline.nreturned

        if ns != None and nr != None:
            if nr == 0:
                # avoid division by 0 errors
                nr = 1
            return (ns > 10000 and ns/nr > 100)

        return False



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
       ('--from', {'action':'store', 'nargs':'*', 'default':'start', 'help':'output starting at FROM', 'dest':'from'}), 
       ('--to',   {'action':'store', 'nargs':'*', 'default':'end',   'help':'output up to TO',         'dest':'to'})
    ]

    timeunits = ['s', 'sec', 'm', 'min', 'h', 'hours', 'd', 'days', 'w', 'weeks', 'mo', 'months', 'y', 'years']
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    dtRegexes = OrderedDict([         
        ('weekday', r'|'.join(weekdays)),                         # weekdays: see above
        ('date',    '('+ '|'.join(months) +')' + r'\s+\d{1,2}'),  # month + day:  Jan 5, Oct 13, Sep 03, ...
        ('word',    r'now|start|end|today|from'),
        ('time2',   r'\d{1,2}:\d{2,2}'),                          # 11:59, 1:13, 00:00, ...
        ('time3',   r'\d{1,2}:\d{2,2}:\d{2,2}'),                  # 11:59:00, 1:13:12, 00:00:59, ...
        ('offset',  r'[\+-]\d+(' + '|'.join(timeunits) + ')'),    # offsets: +3min, -20s, +7days, ...                    
    ])

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)

        self.fromReached = False
        self.toReached = False

        self.fromDateTime = None
        if 'from' in self.commandLineArgs:
            self.fromDateTime = self._interpretDateTime(self.commandLineArgs['from'])
            self.active = True

        if 'to' in self.commandLineArgs:
            self.toDateTime = self._interpretDateTime(self.commandLineArgs['to'], self.fromDateTime)
            self.active = True


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


    def _interpretDateTime(self, timemark, fromTime=None):
        dtdict = {}
        # go through all regexes in order and see which ones match
        for idx in self.dtRegexes:
            tmrx = self.dtRegexes[idx]
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
            elif unit in ['mo', 'months']:
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



