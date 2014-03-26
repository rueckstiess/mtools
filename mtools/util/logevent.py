from datetime import datetime
from dateutil.tz import tzutc
import dateutil.parser
import re
import json

from mtools.util.pattern import json2pattern


class DateTimeEncoder(json.JSONEncoder):
    """ custom datetime encoder for json output. """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class LogEvent(object):
    """ LogEvent extracts information from a mongod/mongos log file line and
        stores the following properties/variables:

        line_str: the original line string
        split_tokens: a list of string tokens after splitting line_str using
                      whitespace as split points
        datetime: a datetime object for the logevent. For logfiles created with
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


    def __init__(self, doc_or_str):
        self._year_rollover = False

        if isinstance(doc_or_str, str):
            # create from string, remove line breaks at end of _line_str
            self.from_string = True
            self._line_str = doc_or_str.rstrip()
            self._profile_doc = None
            self._reset()
        else:
            self.from_string = False
            self._profile_doc = doc_or_str
            # docs don't need to be parsed lazily, they are fast
            self._parse_document()



    def _reset(self):
        self._split_tokens_calculated = False
        self._split_tokens = None

        self._duration_calculated = False
        self._duration = None

        self._datetime_calculated = False
        self._datetime = None
        self._datetime_nextpos = None
        self._datetime_format = None
        self._datetime_str = ''

        self._thread_calculated = False
        self._thread = None

        self._operation_calculated = False
        self._operation = None
        self._namespace = None

        self._pattern = None
        self._sort_pattern = None

        self._counters_calculated = False
        self._nscanned = None
        self._ntoreturn = None
        self._nupdated = None
        self._nreturned = None
        self._ninserted = None
        self._ndeleted = None
        self._numYields = None
        self._r = None
        self._w = None

        self.merge_marker_str = ''

    def set_line_str(self, line_str):
        """ line_str is only writeable if LogEvent was created from a string, not from a system.profile documents. """

        if not self.from_string:
            raise ValueError("can't set line_str for LogEvent created from system.profile documents.")

        if line_str != self._line_str:
            self._line_str = line_str.rstrip()
            self._reset()


    def get_line_str(self):
        """ return line_str depending on source, logfile or system.profile. """

        if self.from_string:
            return ' '.join([s for s in [self.merge_marker_str, self._datetime_str, self._line_str] if s])
        else:
            return ' '.join([s for s in [self._datetime_str, self._line_str] if s])

    line_str = property(get_line_str, set_line_str)


    @property
    def split_tokens(self):
        """ splits string into tokens (lazy) """

        if not self._split_tokens_calculated:
            # split into items (whitespace split)
            self._split_tokens = self._line_str.split()
            self._split_tokens_calculated = True

        return self._split_tokens


    @property
    def duration(self):
        """ calculate duration if available (lazy) """

        if not self._duration_calculated:
            self._duration_calculated = True

            # split_tokens = self.split_tokens
            line_str = self.line_str

            if line_str and line_str.endswith('ms'):
                try:
                    # find duration from end
                    space_pos = line_str.rfind(" ")
                    if space_pos == -1:
                        return
                    self._duration = int(line_str[line_str.rfind(" ")+1:-2].replace(',',''))
                except ValueError:
                    self._duration = None
            elif "flushing" in self.line_str:
                matchobj = re.search(r'flushing mmaps took (\d+)ms', self.line_str)
                if matchobj:
                    self._duration = int(matchobj.group(1))

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
                    self._datetime_nextpos = offs
                    if self._datetime_format.startswith("iso8601"):
                        self._datetime_nextpos += 1
                    else:
                        self._datetime_nextpos += 4

                    # separate datetime str and linestr
                    self._line_str = ' '.join(self.split_tokens[self._datetime_nextpos:])
                    self._reformat_timestamp(self._datetime_format)
                    break

        return self._datetime


    @property
    def datetime_format(self):
        if not self._datetime_calculated:
            _ = self.datetime

        return self._datetime_format


    @property
    def datetime_nextpos(self):
        if self._datetime_nextpos == None and not self._datetime_calculated:
            _ = self.datetime
        return self._datetime_nextpos


    def set_datetime_hint(self, format, nextpos, rollover):
        self._datetime_format = format
        self._datetime_nextpos = nextpos
        self._year_rollover = rollover

        # fast check if timezone changed. if it has, trigger datetime evaluation
        if format.startswith('ctime'):
            if len(self.split_tokens) < 4 or self.split_tokens[self._datetime_nextpos-4] not in self.weekdays:
                _ = self.datetime
                return False
            return True
        else:
            if not self.split_tokens[self._datetime_nextpos-1][0].isdigit():
                _ = self.datetime
                return False
            return True


    def _match_datetime_pattern(self, tokens):
        """ Helper method that takes a list of tokens and tries to match
            the datetime pattern at the beginning of the token list.

            There are several formats that this method needs to understand
            and distinguish between (see MongoDB's SERVER-7965):

            ctime-pre2.4    Wed Dec 31 19:00:00
            ctime           Wed Dec 31 19:00:00.000
            iso8601-utc     1970-01-01T00:00:00.000Z
            iso8601-local   1969-12-31T19:00:00.000+0500
        """
        # first check: less than 4 tokens can't be ctime
        assume_iso8601_format = len(tokens) < 4

        # check for ctime-pre-2.4 or ctime format
        if not assume_iso8601_format:
            weekday, month, day, time = tokens[:4]
            if len(tokens) < 4 or (weekday not in self.weekdays) or \
               (month not in self.months) or not day.isdigit():
                assume_iso8601_format = True

        if assume_iso8601_format:
            # sanity check, because the dateutil parser could interpret
            # any numbers as a valid date
            if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}', \
                            tokens[0]):
                return None

            # convinced that this is a ISO-8601 format, the dateutil parser
            # will do the rest
            dt = dateutil.parser.parse(tokens[0])
            self._datetime_format = "iso8601-utc" \
                if tokens[0].endswith('Z') else "iso8601-local"

        else:
            # assume current year unless self.year_rollover is set (from LogFile)
            year = datetime.now().year
            dt = dateutil.parser.parse(' '.join(tokens[:4]), default=datetime(year, 1, 1))

            if dt.tzinfo == None:
                dt = dt.replace(tzinfo=tzutc())

            if self._year_rollover and dt > self._year_rollover:
                dt = dt.replace(year=year-1)

            self._datetime_format = "ctime" \
                if '.' in tokens[3] else "ctime-pre2.4"

        return dt


    @property
    def thread(self):
        """ extract thread name if available (lazy) """

        if not self._thread_calculated:
            self._thread_calculated = True

            split_tokens = self.split_tokens

            if not self.datetime_nextpos or len(split_tokens) <= self.datetime_nextpos:
                return None

            connection_token = split_tokens[self.datetime_nextpos]
            match = re.match(r'^\[([^\]]*)\]$', connection_token)
            if match:
                self._thread = match.group(1)

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
            logevent. It doesn't make sense to only extract one as they
            appear back to back in the token list.
        """

        split_tokens = self.split_tokens

        if not self._datetime_nextpos:
            # force evaluation of datetime to get access to datetime_offset
            _ = self.datetime

        if not self._datetime_nextpos or len(split_tokens) <= self._datetime_nextpos + 2:
            return

        op = split_tokens[self._datetime_nextpos + 1]

        if op in ['query', 'insert', 'update', 'remove', 'getmore', 'command']:
            self._operation = op
            self._namespace = split_tokens[self._datetime_nextpos + 2]



    @property
    def pattern(self):
        """ extract query pattern from operations """

        if not self._pattern:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore', 'update', 'remove']:
                self._pattern = self._find_pattern('query: ')

        return self._pattern

    
    @property
    def sort_pattern(self):
        """ extract query pattern from operations """

        if not self._sort_pattern:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore']:
                self._sort_pattern = self._find_pattern('orderby: ')

        return self._sort_pattern


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
    def ndeleted(self):
        """ extract ndeleted counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ndeleted

    @property
    def nupdated(self):
        """ extract nupdated counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nupdated

    @property
    def numYields(self):
        """ extract numYields counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._numYields

    @property
    def r(self):
        """ extract read lock (r) counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._r

    @property
    def w(self):
        """ extract write lock (w) counter if available (lazy) """

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._w


    def _extract_counters(self):
        """ Helper method to extract counters like nscanned, nreturned, etc.
            from the logevent.
        """

        # extract counters (if present)
        counters = ['nscanned', 'ntoreturn', 'nreturned', 'ninserted', \
            'nupdated', 'ndeleted', 'r', 'w', 'numYields']

        split_tokens = self.split_tokens

        # trigger thread evaluation to get access to offset
        if self.thread:
            for t, token in enumerate(split_tokens[self.datetime_nextpos+2:]):
                for counter in counters:
                    if token.startswith('%s:'%counter):
                        try:
                            vars(self)['_'+counter] = int((token.split(':')[-1]).replace(',', ''))
                        except ValueError:
                            # see if this is a pre-2.5.2 numYields with space in between (e.g. "numYields: 2")
                            # https://jira.mongodb.org/browse/SERVER-10101
                            if counter == 'numYields' and token.startswith('numYields'):
                                try:
                                    self._numYields = int((split_tokens[t+1+self.datetime_nextpos+2]).replace(',', ''))
                                except ValueError:
                                    pass
                        # token not parsable, skip
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
        pattern = self.pattern
        nscanned = self.nscanned
        ntoreturn = self.ntoreturn
        nreturned = self.nreturned
        ninserted = self.ninserted
        ndeleted = self.ndeleted
        nupdated = self.nupdated
        numYields = self.numYields
        w = self.w
        r = self.r


    def _find_pattern(self, trigger):

        # get start of json query pattern
        start_idx = self.line_str.rfind(trigger)
        if start_idx == -1:
            # no query pattern found
            return None

        stop_idx = 0
        brace_counter = 0
        search_str = self.line_str[start_idx+len(trigger):]

        for match in re.finditer(r'{|}', search_str):
            stop_idx = match.start()
            if search_str[stop_idx] == '{':
                brace_counter += 1
            else:
                brace_counter -= 1
            if brace_counter == 0:
                break
        search_str = search_str[:stop_idx+1].strip()
        if search_str:
            return json2pattern(search_str)
        else:
            return None



    def _reformat_timestamp(self, format, force=False):
        if format not in ['ctime', 'ctime-pre2.4', 'iso8601-utc', 'iso8601-local']:
            raise ValueError('invalid datetime format %s, choose from ctime, ctime-pre2.4, iso8601-utc, iso8601-local.')

        if (self.datetime_format == None or (self.datetime_format == format and self._datetime_str != '')) and not force:
            return
        elif self.datetime == None:
            return
        elif format.startswith('ctime'):
            dt_string = self.weekdays[self.datetime.weekday()] + ' ' + self.datetime.strftime("%b %d %H:%M:%S")
            # remove zero-padding from day number
            tokens = dt_string.split(' ')
            if tokens[2].startswith('0'):
                tokens[2] = tokens[2].replace('0', ' ', 1)
            dt_string = ' '.join(tokens)
            if format == 'ctime':
                dt_string += '.' + str(int(self.datetime.microsecond / 1000)).zfill(3)
        elif format == 'iso8601-local':
            dt_string = self.datetime.isoformat()
            if not self.datetime.utcoffset():
                dt_string += '+00:00'
            ms_str = str(int(self.datetime.microsecond * 1000)).zfill(3)[:3]
            # change isoformat string to have 3 digit milliseconds and no : in offset
            dt_string = re.sub(r'(\.\d+)?([+-])(\d\d):(\d\d)', '.%s\\2\\3\\4'%ms_str, dt_string)
        elif format == 'iso8601-utc':
            if self.datetime.utcoffset():
                dt_string = self.datetime.astimezone(tzutc()).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                dt_string = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")
            dt_string += '.' + str(int(self.datetime.microsecond * 1000)).zfill(3)[:3] + 'Z'

        # set new string and format
        self._datetime_str = dt_string
        self._datetime_format = format


    def __str__(self):
        """ default string conversion for a LogEvent object is just its line_str. """
        return str(self.line_str)


    def to_dict(self, labels=None):
        """ converts LogEvent object to a dictionary. """
        output = {}
        if labels == None:
            labels = ['line_str', 'split_tokens', 'datetime', 'operation', \
                'thread', 'namespace', 'nscanned', 'ntoreturn',  \
                'nreturned', 'ninserted', 'nupdated', 'ndeleted', 'duration', 'r', 'w', 'numYields']

        for label in labels:
            value = getattr(self, label, None)
            if value != None:
                output[label] = value

        return output


    def to_json(self, labels=None):
        """ converts LogEvent object to valid JSON. """
        output = self.to_dict(labels)
        return json.dumps(output, cls=DateTimeEncoder, ensure_ascii=False)


    def _parse_document(self):
        """ Parses a system.profile document and copies all the values to the member variables. """
        doc = self._profile_doc

        self._split_tokens_calculated = True
        self._split_tokens = None

        self._duration_calculated = True
        self._duration = doc[u'millis']

        self._datetime_calculated = True
        self._datetime = doc[u'ts']
        if self._datetime.tzinfo == None:
            self._datetime = self._datetime.replace(tzinfo=tzutc())
        self._datetime_format = None
        self._reformat_timestamp('ctime', force=True)

        self._thread_calculated = True
        self._thread = doc['thread']

        self._operation_calculated = True
        self._operation = doc[u'op']
        self._namespace = doc[u'ns']

        # query pattern for system.profile events, all three cases (see SERVER-13245)
        if 'query' in doc:
            if 'query' in doc['query'] and isinstance(doc['query']['query'], dict):
                self._pattern = str(doc['query']['query']).replace("'", '"')
            elif '$query' in doc['query']:
                self._pattern = str(doc['query']['$query']).replace("'", '"')
            else:
                self._pattern = str(doc['query']).replace("'", '"')

            # sort pattern
            if 'orderby' in doc['query'] and isinstance(doc['query']['orderby'], dict):
                self._sort_pattern = str(doc['query']['orderby']).replace("'", '"')    
            elif '$orderby' in doc['query']:
                self._sort_pattern = str(doc['query']['$orderby']).replace("'", '"')
            else: 
                self._sort_pattern = None

        self._counters_calculated = True
        self._nscanned = doc[u'nscanned'] if 'nscanned' in doc else None
        self._ntoreturn = doc[u'ntoreturn'] if 'ntoreturn' in doc else None
        self._nupdated = doc[u'nupdated'] if 'nupdated' in doc else None
        self._nreturned = doc[u'nreturned'] if 'nreturned' in doc else None
        self._ninserted = doc[u'ninserted'] if 'ninserted' in doc else None
        self._ndeleted = doc[u'ndeleted'] if 'ndeleted' in doc else None
        self._numYields = doc[u'numYield'] if 'numYield' in doc else None
        self._r = doc[u'lockStats'][u'timeLockedMicros'][u'r']
        self._w = doc[u'lockStats'][u'timeLockedMicros'][u'w']

        self._r_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'r']
        self._w_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'w']

        # build a fake line_str
        payload = ''
        if 'query' in doc:
            payload += 'query: %s' % str(doc[u'query']).replace("u'", "'").replace("'", '"')
        if 'command' in doc:
            payload += 'command: %s' % str(doc[u'command']).replace("u'", "'").replace("'", '"')
        if 'updateobj' in doc:
            payload += ' update: %s' % str(doc[u'updateobj']).replace("u'", "'").replace("'", '"')

        scanned = 'nscanned:%i'%self._nscanned if 'nscanned' in doc else ''
        yields = 'numYields:%i'%self._numYields if 'numYield' in doc else ''
        locks = 'w:%i' % self.w if self.w != None else 'r:%i' % self.r
        duration = '%ims' % self.duration if self.duration != None else ''

        self._line_str = "[{thread}] {operation} {namespace} {payload} {scanned} {yields} locks(micros) {locks} {duration}".format(
            datetime=self.datetime, thread=self.thread, operation=self.operation, namespace=self.namespace, payload=payload, scanned=scanned, yields=yields, locks=locks, duration=duration)
