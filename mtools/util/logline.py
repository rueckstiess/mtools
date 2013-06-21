from datetime import datetime
import re
import json

class DateTimeEncoder(json.JSONEncoder):
    """ custom datetime encoder for json output. """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class LogLine(object):
    """ LogLine extracts information from a mongod/mongos log file line and 
        stores the following properties/variables:

        line_str: the original line string
        split_tokens: a list of string tokens after splitting line_str using 
                      whitespace as split points
        datetime: a datetime object for the logline. For logfiles created with 
                  version 2.4+, it also contains micro-seconds
        duration: the duration of a timed operation in ms
        thread: the thread name (e.g. "conn1234") as string
        operation: insert, update, remove, query, command, getmore, None
        namespace: the namespace of the operation, or None
        
        Certain operations also add the number of affected/scanned documents.
        If applicable, the following variables are also set, otherwise the 
        default is None: nscanned, ntoreturn, nreturned, ninserted, nupdated

        For performance reason, all fields are evaluated lazily upon first
        request.
    """

    # datetime handler for json encoding
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, \
        datetime) else None

    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', \
        'Oct', 'Nov', 'Dec']


    def __init__(self, line_str, auto_parse=True):
        # remove line breaks at end of line_str
        self.line_str = line_str.rstrip('\n')

        self._split_tokens_calculated = False
        self._split_tokens = None

        self._duration_calculated = False
        self._duration = None

        self._datetime_calculated = False
        self._datetime = None
        self._datetime_offset = None

        self._thread_calculated = False
        self._thread = None
        self._thread_offset = None

        self._operation_calculated = False
        self._operation = None
        self._namespace = None

        self._counters_calculated = False
        self._nscanned = None
        self._ntoreturn = None
        self._nupdated = None
        self._nreturned = None
        self._ninserted = None


    @property
    def split_tokens(self):
        """ splits string into tokens (lazy) """

        if not self._split_tokens_calculated:
            # split into items (whitespace split)
            self._split_tokens = self.line_str.split()
            self._split_tokens_calculated = True

        return self._split_tokens


    @property
    def duration(self):
        """ calculate duration if available (lazy) """
        
        if not self._duration_calculated:
            self._duration_calculated = True

            split_tokens = self.split_tokens

            # if len(split_tokens) > 0 and split_tokens[-1].endswith('ms'):
            if len(split_tokens) > 0 and re.match(r'[0-9]{1,}ms$', split_tokens[-1]):
                self._duration = int(split_tokens[-1][:-2])

        return self._duration


    @property
    def datetime(self):
        """ extract datetime if available (lazy) """

        if not self._datetime_calculated:
            self._datetime_calculated = True

            # if no datetime after 10 tokens, break to avoid parsing very long lines
            split_tokens = self.split_tokens[:10]

            match_found = False
            for offs in xrange(len(split_tokens)):
                dt = self._match_datetime_pattern(split_tokens[offs:offs+4])
                if dt:
                    self._datetime = dt
                    self._datetime_offset = offs
                    break

        return self._datetime


    def _match_datetime_pattern(self, tokens):
        """ Helper method that takes a list of tokens and tries to match the 
            datetime pattern at the beginning of the token list, i.e. the first
            few tokens need to match [weekday], [month], [day], HH:MM:SS  
            (potentially with milliseconds for mongodb version 2.4+). """
        
        if len(tokens) < 4:
            return None

        # return None
        weekday, month, day, time = tokens[:4]

        # check if it is a valid datetime
        if (weekday not in self.weekdays) or \
           (month not in self.months) or not day.isdigit():
            return None

        time_match = re.match(r'(\d{2}):(\d{2}):(\d{2})(\.\d{3})?', time)
        if not time_match:
            return None

        month = self.months.index(month)+1

        # extract hours, min, sec, millisec from time string
        h, m, s, ms = time_match.groups()

        # old format (pre 2.4) has no ms set to 0
        if ms == None:
            ms = 0
        else:
            ms = int(ms[1:])

        # convert to microsec for datetime
        ms *= 1000

        # assume this year. TODO: special case if logfile is not from current year
        year = datetime.now().year

        dt = datetime(int(year), int(month), int(day), int(h), int(m), int(s), ms)

        return dt


    @property
    def thread(self):
        """ extract thread name if available (lazy) """

        if not self._thread_calculated:
            self._thread_calculated = True

            split_tokens = self.split_tokens

            # force evaluation of datetime to get access to datetime_offset
            if self.datetime:
                if len(split_tokens) <= self._datetime_offset + 4:
                    return None

                connection_token = split_tokens[self._datetime_offset + 4]
                match = re.match(r'^\[([^\]]*)\]$', connection_token)
                if match:
                    self._thread = match.group(1)
                    self._thread_offset = self._datetime_offset + 4
  
        return self._thread


    @property
    def operation(self):
        """ extract operation (query, insert, update, remove, getmore, command) 
            if available (lazy) """

        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._operation


    @property
    def namespace(self):
        """ extract namespace if available (lazy) """

        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._namespace


    def _extract_operation_and_namespace(self):
        """ Helper method to extract both operation and namespace from a 
            logline. It doesn't make sense to only extract one as they
            appear back to back in the token list.
        """

        split_tokens = self.split_tokens

        # trigger datetime evaluation to get access to offset
        if self.datetime:
            if len(split_tokens) <= self._datetime_offset + 6:
                return
            op = split_tokens[self._datetime_offset + 5]

            if op in ['query', 'insert', 'update', 'remove', 'getmore', 'command']:
                self._operation = op
                self._namespace = split_tokens[self._datetime_offset + 6]



    @property
    def nscanned(self):
        """ extract nscanned counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscanned

    @property
    def ntoreturn(self):
        """ extract ntoreturn counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ntoreturn


    @property
    def nreturned(self):
        """ extract nreturned counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nreturned


    @property
    def ninserted(self):
        """ extract ninserted counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ninserted

    @property
    def nupdated(self):
        """ extract nupdated counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nupdated



    def _extract_counters(self):
        """ Helper method to extract counters like nscanned, nreturned, etc.
            from the logline. 
        """

        # extract n-values (if present)
        counters = ['nscanned', 'ntoreturn', 'nreturned', 'ninserted', \
            'nupdated']

        split_tokens = self.split_tokens

        # trigger thread evaluation to get access to offset
        if self.thread:
            for token in split_tokens[self._thread_offset+2:]:
                for counter in counters:
                    if token.startswith('%s:'%counter):
                        vars(self)['_'+counter] = int(token.split(':')[-1])
                        break


    def parse_all(self):
        """ triggers the extraction of all information, which would usually
            just be evaluated lazily. 
        """
        tokens = self.split_tokens
        duration = self.duration
        datetime = self.datetime
        thread = self.thread
        operation = self.operation
        namespace = self.namespace
        nscanned = self.nscanned
        ntoreturn = self.ntoreturn
        nreturned = self.nreturned
        ninserted = self.ninserted
        nupdated = self.nupdated


    def __str__(self):
        """ default string conversion for a LogLine object. """
        output = ''
        labels = ['line_str', 'split_tokens', 'datetime', 'operation', \
                  'thread', 'namespace', 'nscanned', 'ntoreturn',  \
                  'nreturned', 'ninserted', 'nupdated', 'duration']

        for label in labels:
            value = getattr(self, label, None)
            if value != None:
                output += '%s:'%label
                output += str(value)
                output += ' '

        return output


    def to_dict(self, labels=None):
        """ converts LogLine object to a dictionary. """
        output = {}
        if labels == None:
            labels = ['line_str', 'split_tokens', 'datetime', 'operation', \
                'thread', 'namespace', 'nscanned', 'ntoreturn',  \
                'nreturned', 'ninserted', 'nupdated', 'duration']

        for label in labels:
            value = getattr(self, label, None)
            if value != None:
                output[label] = value

        return output     

    
    def to_json(self, labels=None):
        """ converts LogLine object to valid JSON. """
        output = self.to_dict(labels)
        return json.dumps(output, cls=DateTimeEncoder)





