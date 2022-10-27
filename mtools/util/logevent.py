#!/usr/bin/env python3

import json
import re
import sys
from datetime import datetime

import dateutil.parser
from dateutil.tz import tzutc

from mtools.util.pattern import json2pattern


class DateTimeEncoder(json.JSONEncoder):
    """Custom datetime encoder for json output."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class LogEvent(object):
    """
    Extract information from log line and store properties/variables.
    line_str: the original line string
    split_tokens: a list of string tokens after splitting line_str using
                  whitespace as split points
    datetime: a datetime object for the logevent. For logfiles created with
              version 2.4+, it also contains micro-seconds
    duration: the duration of a timed operation in ms
    thread: the thread name (e.g. "conn1234") as string
    operation: insert, update, remove, query, command, getmore, None
    namespace: the namespace of the operation, or None
    command: the type of command, if the operation was a "command"
    pattern: the query pattern for queries, updates, counts, etc
    ...
    Certain operations also add the number of affected/scanned documents.
    If applicable, the following variables are also set, otherwise the
    default is None: nscanned, ntoreturn, nreturned, ninserted, nupdated
    For performance reason, all fields are evaluated lazily upon first
    request.
    """

    # datetime handler for json encoding
    dthandler = lambda obj: obj.isoformat() if isinstance(obj,
                                                          datetime) else None

    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
              'Oct', 'Nov', 'Dec']

    log_operations = ['query', 'insert', 'update', 'remove', 'getmore',
                      'command', 'aggregate', 'transaction']
    log_levels = ['D', 'F', 'E', 'W', 'I', 'U']
    log_components = ['-', 'ACCESS', 'COMMAND', 'CONTROL', 'GEO', 'INDEX',
                      'NETWORK', 'QUERY', 'REPL', 'SHARDING', 'STORAGE',
                      'JOURNAL', 'WRITE', 'TOTAL']

    def __init__(self, doc_or_str):
        self._debug = False
        self._year_rollover = False
        if isinstance(doc_or_str, bytes):
            doc_or_str = doc_or_str.decode("utf-8")

        if isinstance(doc_or_str, str) or (sys.version_info.major == 2 and
                                           isinstance(doc_or_str, unicode)):
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
        self._debug = False
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
        self._actual_query = None
        self._actual_sort = None

        # SERVER-36414 - parameters for slow transactions
        self._lsid = None
        self._txnNumber = None
        self._autocommit = None
        self._readConcern = None
        self._timeActiveMicros = None
        self._timeInactiveMicros = None
        self._readTimestamp = None
        self._terminationCause = None
        self._locks = None

        self._command_calculated = False
        self._command = None

        self._counters_calculated = False
        self._allowDiskUse = None

        self._bytesRead = None
        self._bytesWritten = None
        self._timeReadingMicros = None
        self._timeWritingMicros = None

        # TODO: refactor from the legacy names to modern
        # (eg: nscanned => keysExamined). Currently _extract_counters()
        # maps newer property names into legacy equivalents for
        # broader log file support.
        self._nscanned = None         # keysExamined
        self._nscannedObjects = None  # docsExamined
        self._ntoreturn = None
        self._nupdated = None         # nModified
        self._nreturned = None        # nReturned or nMatched (updates)
        self._ninserted = None        # nInserted
        self._ndeleted = None         # nDeleted

        self._numYields = None
        self._planSummary = None
        self._actualPlanSummary = None
        self._writeConflicts = None
        self._r = None
        self._w = None
        self._conn = None
        self._hostname = None

        self._level_calculated = False
        self._level = None
        self._component = None
        self.merge_marker_str = ''

        self._client_metadata_calculated = False
        self._client_metadata = None

    def set_line_str(self, line_str):
        """
        Set line_str.
        Line_str is only writeable if LogEvent was created from a string,
        not from a system.profile documents.
        """
        if not self.from_string:
            raise ValueError("can't set line_str for LogEvent created from "
                             "system.profile documents.")

        if line_str != self._line_str:
            self._line_str = line_str.rstrip()
            self._reset()

    def get_line_str(self):
        """Return line_str depending on source, logfile or system.profile."""
        if self.from_string:
            return ' '.join([s for s in [self.merge_marker_str,
                                         self._datetime_str,
                                         self._line_str] if s])
        else:
            return ' '.join([s for s in [self._datetime_str,
                                         self._line_str] if s])

    line_str = property(get_line_str, set_line_str)

    @property
    def split_tokens(self):
        """Split string into tokens (lazy)."""
        if not self._split_tokens_calculated:
            # split into items (whitespace split)
            self._split_tokens = self._line_str.split()
            self._split_tokens_calculated = True

        return self._split_tokens

    @property
    def duration(self):
        """Calculate duration if available (lazy)."""
        if not self._duration_calculated:
            self._duration_calculated = True

            # split_tokens = self.split_tokens
            line_str = self.line_str

            if (line_str
                and line_str.endswith('ms')
                and 'Scheduled new oplog query' not in line_str):

                try:
                    # find duration from end
                    space_pos = line_str.rfind(" ")
                    if space_pos == -1:
                        return
                    self._duration = int(line_str[line_str.rfind(" ") +
                                                  1:-2].replace(',', ''))
                except ValueError:
                    self._duration = None
            elif "flushing" in self.line_str:
                matchobj = re.search(r'flushing mmaps took (\d+)ms',
                                     self.line_str)
                if matchobj:
                    self._duration = int(matchobj.group(1))
            # SERVER-16176 - Logging of slow checkpoints
            elif "Checkpoint took" in self.line_str:
                matchobj = re.search("Checkpoint took ([\d]+) seconds to complete", self.line_str)
                if matchobj:
                    self._duration = int(matchobj.group(1)) * 1000

        return self._duration

    # SERVER-41349 - get hostname from the DNS log line
    @property
    def hostname(self):
        line_str = self.line_str
        groups = re.search("DNS resolution while connecting to ([\w.]+) took ([\d]+)ms", line_str)
        self._hostname = groups.group(1)
        return self._hostname


    @property
    def cursor(self):
        """Pull the cursor information if available (lazy)."""
        line_str = self.line_str
        # SERVER-28604 Checking reaped cursor information
        groups = re.search("Cursor id ([\w.]+) timed out, idle since ([^\n]*)", line_str)
        self._cursorid = groups.group(1)
        self._reapedtime = groups.group(2)

        return self._cursorid

    @property
    def datetime(self):
        """Extract datetime if available (lazy)."""
        if not self._datetime_calculated:
            self._datetime_calculated = True

            # if no datetime after 10 tokens, break to avoid parsing
            # very long lines
            split_tokens = self.split_tokens[:10]

            for offs in range(len(split_tokens)):
                dt = self._match_datetime_pattern(split_tokens[offs:offs + 4])
                if dt:
                    self._datetime = dt
                    self._datetime_nextpos = offs
                    if self._datetime_format.startswith("iso8601"):
                        self._datetime_nextpos += 1
                    else:
                        self._datetime_nextpos += 4

                    # separate datetime str and linestr
                    self._line_str = (' '.join(self.split_tokens
                                               [self._datetime_nextpos:]))

                    if self.level:
                        self._datetime_nextpos += 2

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
        if self._datetime_nextpos is None and not self._datetime_calculated:
            _ = self.datetime
        return self._datetime_nextpos

    def set_datetime_hint(self, format, nextpos, rollover):
        self._datetime_format = format
        self._datetime_nextpos = nextpos
        self._year_rollover = rollover

        # Fast check if timestamp format changed.
        # If it has, trigger datetime evaluation.
        if format.startswith('ctime'):
            if (len(self.split_tokens) < 4 or
                    self.split_tokens[self._datetime_nextpos - 4] not in
                    self.weekdays):
                _ = self.datetime
                return False
            return True
        else:
            if len(self.split_tokens) == 0:
                # empty line, no need to parse datetime
                self._datetime_calculated = True
                return False
            try:
                if not (self.split_tokens[self._datetime_nextpos - 1][0]
                        .isdigit()):
                    # not the timestamp format that was hinted
                    _ = self.datetime
                    return False
            except Exception:
                pass
            return True

    def _match_datetime_pattern(self, tokens):
        """
        Match the datetime pattern at the beginning of the token list.
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
            if (len(tokens) < 4 or (weekday not in self.weekdays) or
                    (month not in self.months) or not day.isdigit()):
                assume_iso8601_format = True

        if assume_iso8601_format:
            # sanity check, because the dateutil parser could interpret
            # any numbers as a valid date
            if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}',
                            tokens[0]):
                return None

            # convinced that this is a ISO-8601 format, the dateutil parser
            # will do the rest
            dt = dateutil.parser.parse(tokens[0])
            self._datetime_format = "iso8601-utc" \
                if tokens[0].endswith('Z') else "iso8601-local"

        else:
            # assume current year unless self.year_rollover
            # is set (from LogFile)
            year = datetime.now().year
            dt = dateutil.parser.parse(' '.join(tokens[: 4]),
                                       default=datetime(year, 1, 1))

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tzutc())

            if self._year_rollover and dt > self._year_rollover:
                dt = dt.replace(year=year - 1)

            self._datetime_format = "ctime" \
                if '.' in tokens[3] else "ctime-pre2.4"

        return dt

    @property
    def thread(self):
        """Extract thread name if available (lazy)."""
        if not self._thread_calculated:
            self._thread_calculated = True

            split_tokens = self.split_tokens

            if not self.datetime_nextpos:
                return None
            if len(split_tokens) <= self.datetime_nextpos:
                return None

            connection_token = split_tokens[self.datetime_nextpos]
            match = re.match(r'^\[([^\]]*)\]$', connection_token)
            if match:
                self._thread = match.group(1)

            if self._thread is not None:
                if self._thread in ['initandlisten', 'mongosMain']:
                    if len(split_tokens) >= 5 and split_tokens[-5][0] == '#':
                        self._conn = 'conn' + split_tokens[-5][1:]
                elif self._thread.startswith('conn'):
                    self._conn = self._thread
        return self._thread

    @property
    def conn(self):
        r"""
        Extract conn name if available (lazy).
        This value is None for all lines except the log lines related to
        connections, that is lines matching '\[conn[0-9]+\]' or
        '\[(initandlisten|mongosMain)\] .* connection accepted from'.
        """
        self.thread
        return self._conn

    @property
    def operation(self):
        """
        Extract operation if available (lazy).
        Operations: query, insert, update, remove, getmore, command
        """
        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._operation

    @property
    def namespace(self):
        """Extract namespace if available (lazy)."""
        if not self._operation_calculated:
            self._operation_calculated = True
            self._extract_operation_and_namespace()

        return self._namespace

    def _extract_operation_and_namespace(self):
        """
        Helper method to extract both operation and namespace from a logevent.
        It doesn't make sense to only extract one as they appear back to back
        in the token list.
        """
        split_tokens = self.split_tokens

        if not self._datetime_nextpos:
            # force evaluation of thread to get access to datetime_offset and
            # to protect from changes due to line truncation.
            _ = self.thread

        if not self._datetime_nextpos or (len(split_tokens) <=
                                          self._datetime_nextpos + 2):
            return

        op = split_tokens[self._datetime_nextpos + 1].lower()

        if op == 'warning:':
            # check if this log line got truncated
            if ("warning: log line attempted" in self._line_str and
                    "over max size" in self._line_str):
                self._datetime_nextpos = split_tokens.index('...')
                op = split_tokens[self._datetime_nextpos + 1]
            else:
                # unknown warning, bail out
                return

        if op in self.log_operations:
            self._operation = op
            self._namespace = split_tokens[self._datetime_nextpos + 2]

    @property
    def pattern(self):
        """Extract query pattern from operations."""
        if not self._pattern:

            # trigger evaluation of operation
            if (self.operation in ['query', 'getmore', 'update', 'remove'] or
                    self.command in ['count', 'findandmodify']):
                self._pattern = self._find_pattern('query: ')
                # Fallback check for q: variation (eg "remove" command in 3.6+)
                if self._pattern is None:
                    self._pattern = self._find_pattern('q: ')
            elif self.command == 'find':
                self._pattern = self._find_pattern('filter: ')

        return self._pattern

    @property
    def sort_pattern(self):
        """Extract query pattern from operations."""
        if not self._sort_pattern:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore']:
                self._sort_pattern = self._find_pattern('orderby: ')

        return self._sort_pattern

    @property
    def actual_query(self):
        """Extract the actual query (not pattern) from operations."""
        if not self._actual_query:

            # trigger evaluation of operation
            if (self.operation in ['query', 'getmore', 'update', 'remove'] or
                    self.command in ['count', 'findandmodify']):
                self._actual_query = self._find_pattern('query: ', actual=True)
            elif self.command == 'find':
                self._actual_query = self._find_pattern('filter: ',
                                                        actual=True)

        return self._actual_query

    @property
    def actual_sort(self):
        """Extract the actual sort key (not pattern) from operations."""
        if not self._actual_sort:

            # trigger evaluation of operation
            if self.operation in ['query', 'getmore']:
                self._actual_sort = self._find_pattern('orderby: ',
                                                        actual=True)

        return self._actual_sort

    @property
    def command(self):
        """Extract query pattern from operations."""
        if not self._command_calculated:

            self._command_calculated = True
            if self.operation == 'command':
                try:
                    command_idx = self.split_tokens.index('command:')
                    command = self.split_tokens[command_idx + 1]
                    if command == '{':
                        # workaround for <= 2.2 log files,
                        # where command was not listed separately
                        command = self.split_tokens[command_idx + 2][:-1]
                    self._command = command.lower()
                except ValueError:
                    pass

        return self._command

    @property
    def nscanned(self):
        """Extract nscanned or keysExamined counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscanned

    @property
    def timeActiveMicros(self):
        """Extract timeActiveMicros if available (lazy)."""

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeActiveMicros

    @property
    def timeInactiveMicros(self):
        """Extract timeInactiveMicros if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeInactiveMicros

    @property
    def nscannedObjects(self):
        """
        Extract counters if available (lazy).
        Looks for nscannedObjects or docsExamined.
        """
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscannedObjects

    @property
    def ntoreturn(self):
        """Extract ntoreturn counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ntoreturn

    @property
    def writeConflicts(self):
        """Extract ntoreturn counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._writeConflicts

    @property
    def nreturned(self):
        """
        Extract counters if available (lazy).
        Looks for nreturned, nReturned, or nMatched counter.
        """
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nreturned

    @property
    def terminationCause(self):

        # Looks for terminationCause counter in Transaction logs.

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._terminationCause

    @property
    def ninserted(self):
        """Extract ninserted or nInserted counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ninserted

    @property
    def bytesRead(self):
        """Extract bytesRead counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._bytesRead

    @property
    def bytesWritten(self):
        """Extract bytesWritten counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._bytesWritten

    @property
    def timeReadingMicros(self):
        """Extract timeReadingMicros counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeReadingMicros

    @property
    def timeWritingMicros(self):
        """Extract timeWritingMicros counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeWritingMicros

    @property
    def ndeleted(self):
        """Extract ndeleted or nDeleted counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ndeleted

    @property
    def allowDiskUse(self):
        """Extract allowDiskUse counter for aggregation if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._allowDiskUse

    @property
    def nupdated(self):
        """Extract nupdated or nModified counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nupdated

    @property
    def numYields(self):
        """Extract numYields counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._numYields

    @property
    def readTimestamp(self):
        """Extract readTimeStamp counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._readTimestamp

    @property
    def planSummary(self):
        """Extract planSummary if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._planSummary

    @property
    def actualPlanSummary(self):
        """Extract planSummary including JSON if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._actualPlanSummary

    @property
    def r(self):
        """Extract read lock (r) counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._r

    @property
    def lsid(self):

        """Extract lsid counter if available (lazy)."""
        self._lsid = self._find_pattern('lsid: ', actual=True)
        return self._lsid

    @property
    def locks(self):
        """Extract locks counter for transactions if available (lazy)."""
        self._locks = self._find_pattern('locks:', actual=True)

        return self._locks

    @property
    def txnNumber(self):
        """Extract txnNumber counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._txnNumber

    @property
    def autocommit(self):

        """Extract autocommit counter for transactions if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._autocommit

    @property
    def readConcern(self):

        """Extract readConcern Level if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._readConcern

    @property
    def w(self):
        """Extract write lock (w) counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._w

    def _extract_counters(self):
        """Extract counters like nscanned and nreturned from the logevent."""
        # extract counters (if present)
        counters = ['nscanned', 'nscannedObjects', 'ntoreturn', 'nreturned',
                    'ninserted', 'nupdated', 'ndeleted', 'r', 'w', 'numYields',
                    'planSummary', 'writeConflicts', 'keyUpdates', 'bytesRead', 'bytesWritten', 'timeReadingMicros',
                    'timeWritingMicros', 'lsid', 'txnNumber', 'autocommit',  'allowDiskUse', 'level',
                    'timeActiveMicros', 'timeInactiveMicros', 'duration', 'readTimestamp', 'terminationCause']

        # TODO: refactor mtools to use current counter names throughout
        # Transitionary hack: mapping of current names into prior equivalents
        counter_equiv = {
            'datetime': 'datetime',
            'docsExamined': 'nscannedObjects',
            'keysExamined': 'nscanned',
            'nDeleted': 'ndeleted',
            'nInserted': 'ninserted',
            'nMatched': 'nreturned',
            'nModified': 'nupdated',
            'cursorid' : 'cursorid',
            'repaedtime' : 'reapedtime'
        }
        counters.extend(counter_equiv.keys())

        split_tokens = self.split_tokens

        # trigger operation evaluation to get access to offset
        if self.operation:
            for t, token in enumerate(split_tokens[self.datetime_nextpos +
                                                   2:]):
                for counter in counters:
                    if token.startswith('%s:' % counter):
                        try:
                            # Remap counter to standard name, if applicable
                            counter = counter_equiv.get(counter, counter)
                            if (counter == 'level' and token.startswith('level')):
                                    self._readConcern = (
                                    split_tokens[t + 1 + self.datetime_nextpos + 2].replace(',', ''))
                            elif (counter == 'readTimestamp' and token.startswith('readTimestamp')):
                                vars(self)['_' + counter] = (token.split(':')
                                [-1]).replace(',', '')
                            elif (counter == 'terminationCause' and token.startswith('terminationCause')):
                                vars(self)['_' + counter] = (token.split(':')
                                [-1]).replace(',', '')
                            else:
                                vars(self)['_' + counter] = int((token.split(':')
                                                             [-1]).replace(',',
                                                                           ''))

                            # extract allowDiskUse counter
                            if (counter == 'allowDiskUse' and token.startswith('allowDiskUse')):
                                # Splitting space between token and value
                                self._allowDiskUse = split_tokens[t + 1 + self.datetime_nextpos + 2].replace(',','')
                            else:
                                vars(self)['_' + counter] = int((token.split(':')[-1]).replace(',', ''))

                        except ValueError:
                            # see if this is a pre-2.5.2 numYields with space
                            # in between (e.g. "numYields: 2")
                            # https://jira.mongodb.org/browse/SERVER-10101
                            if (counter == 'numYields' and
                                    token.startswith('numYields')):
                                try:
                                    self._numYields = int((split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                                except ValueError:
                                    pass

                            if (counter == 'bytesRead' and
                                    token.startswith('bytesRead')):
                                try:
                                    self._bytesRead = int((split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                                except ValueError:
                                    pass
                            if (counter == 'bytesWritten' and
                                    token.startswith('bytesWritten')):
                                try:
                                    self._bytesWritten = int(
                                        (split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                                except ValueError:
                                    pass
                            if (counter == 'timeReadingMicros' and
                                    token.startswith('timeReadingMicros')):
                                try:
                                    self._timeReadingMicros = int(
                                        (split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                                except ValueError:
                                    pass
                            if (counter == 'timeWritingMicros' and
                                    token.startswith('timeWritingMicros')):
                                try:
                                    self._timeWritingMicros = int(
                                        (split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                                except ValueError:
                                    pass
                            if (counter == 'txnNumber' and
                                    token.startswith('txnNumber')):
                                    self._txnNumber = int((split_tokens[t + 1 + self.datetime_nextpos + 2]).replace(',', ''))
                            if (counter == 'autocommit' and
                                    token.startswith('autocommit')):
                                    self._autocommit = (split_tokens[t + 1 + self.datetime_nextpos + 2].replace(',', ''))
                            if (counter == 'lsid' and
                                    token.startswith('lsid')):
                                    self._lsid = (split_tokens[t + 2 + self.datetime_nextpos + 2].replace(',', ''))
                            if (counter == 'planSummary' and
                                    token.startswith('planSummary')):
                                try:
                                    self._planSummary = split_tokens[t + 1 + self.datetime_nextpos + 2]
                                    if self._planSummary:
                                        if split_tokens[t + 1 + self.datetime_nextpos + 3] != '{':
                                            self._actualPlanSummary = self._planSummary
                                        else:
                                            self._actualPlanSummary = '%s %s' % (
                                                self._planSummary,
                                                self._find_pattern('planSummary: %s' % self._planSummary, actual=True)
                                            )
                                except ValueError:
                                    pass

                        # token not parsable, skip
                        break

    @property
    def level(self):
        """Extract log level if available (lazy)."""
        if not self._level_calculated:
            self._level_calculated = True
            self._extract_level()
        return self._level

    @property
    def component(self):
        """Extract log component if available (lazy)."""
        self.level
        return self._component

    def _extract_level(self):
        """Extract level and component if available (lazy)."""
        if self._level is None:
            split_tokens = self.split_tokens

            if not split_tokens:
                self._level = False
                self._component = False
                return

            x = (self.log_levels.index(split_tokens[1])
                 if split_tokens[1] in self.log_levels else None)

            if x is not None:
                self._level = split_tokens[1]
                self._component = split_tokens[2]
            else:
                self._level = False
                self._component = False

    @property
    def client_metadata(self):
        """Return client metadata."""
        if not self._client_metadata_calculated:
            self._client_metadata_calculated = True

            line_str = self.line_str
            if (line_str and line_str.find('client metadata')):
                try:
                    metadata_pos = line_str.find("{")
                    if metadata_pos == -1:
                        return
                    else:
                        metadata = line_str[metadata_pos:]
                        # Make valid JSON by wrapping field names in quotes
                        metadata, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:',
                                              ' \\1 "\\2" : ', metadata)

                        # Replace double-quoted platform values with single quote
                        platform = re.search(r'"?platform"?\s*:\s+"(.*?)"', metadata)
                        if (platform):
                            platform = platform.group(1)
                            platform_esc, _ = re.subn(r'"', r"'", platform)
                            metadata, _ = re.subn(platform, platform_esc, metadata)

                        self._client_metadata = json.loads(metadata)
                except ValueError:
                    self._client_metadata = None

        return self._client_metadata

    def parse_all(self):
        """
        Trigger extraction of all information.
        These values are usually evaluated lazily.
        """
        tokens = self.split_tokens
        duration = self.duration
        datetime = self.datetime
        thread = self.thread
        operation = self.operation
        namespace = self.namespace
        pattern = self.pattern
        nscanned = self.nscanned
        nscannedObjects = self.nscannedObjects
        ntoreturn = self.ntoreturn
        nreturned = self.nreturned
        ninserted = self.ninserted
        ndeleted = self.ndeleted
        nupdated = self.nupdated
        numYields = self.numYields
        txnNumber = self.txnNumber
        w = self.w
        r = self.r

    def _find_pattern(self, trigger, actual=False):
        # get start of json query pattern
        start_idx = self.line_str.rfind(trigger)
        if start_idx == -1:
            # no query pattern found
            return None

        stop_idx = 0
        brace_counter = 0
        search_str = self.line_str[start_idx + len(trigger):]

        for match in re.finditer(r'{|}', search_str):
            stop_idx = match.start()
            if search_str[stop_idx] == '{':
                brace_counter += 1
            else:
                brace_counter -= 1
            if brace_counter == 0:
                break
        search_str = search_str[:stop_idx + 1].strip()
        if search_str:
            if actual:
                return search_str
            else:
                return json2pattern(search_str, debug=self._debug)
        else:
            return None

    def _reformat_timestamp(self, format, force=False):
        if format not in ['ctime', 'ctime-pre2.4', 'iso8601-utc',
                          'iso8601-local']:
            raise ValueError('invalid datetime format %s, choose from ctime, '
                             'ctime-pre2.4, iso8601-utc, iso8601-local.')

        if ((self.datetime_format is None or
                (self.datetime_format == format and
                    self._datetime_str != '')) and not force):
            return
        elif self.datetime is None:
            return
        elif format.startswith('ctime'):
            dt_string = (self.weekdays[self.datetime.weekday()] + ' ' +
                         self.datetime.strftime("%b %d %H:%M:%S"))
            # remove zero-padding from day number
            tokens = dt_string.split(' ')
            if tokens[2].startswith('0'):
                tokens[2] = tokens[2].replace('0', ' ', 1)
            dt_string = ' '.join(tokens)
            if format == 'ctime':
                dt_string += '.' + str(int(self.datetime.microsecond /
                                           1000)).zfill(3)
        elif format == 'iso8601-local':
            dt_string = self.datetime.isoformat()
            if self.datetime.utcoffset() is None:
                dt_string += '+00:00'
            ms_str = str(int(self.datetime.microsecond / 1000)).zfill(3)[:3]
            # change isoformat string to have 3 digit milliseconds and no :
            # in offset
            dt_string = re.sub(r'(\.\d+)?([+-])(\d\d):(\d\d)',
                               '.%s\\2\\3\\4' % ms_str, dt_string, count=1)
        elif format == 'iso8601-utc':
            if self.datetime.utcoffset():
                dt_string = self.datetime.astimezone(tzutc()).strftime("%Y-%m-"
                                                                       "%dT%H:"
                                                                       "%M:%S")
            else:
                dt_string = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")
            dt_string += '.' + str(int(self.datetime.microsecond /
                                       1000)).zfill(3)[:3] + 'Z'

        # set new string and format
        self._datetime_str = dt_string
        self._datetime_format = format

    def __str__(self):
        """Default string conversion for LogEvent object is its line_str."""
        return str(self.line_str)

    def to_dict(self, labels=None):
        """Convert LogEvent object to a dictionary."""
        output = {}
        if labels is None:
            labels = ['line_str', 'split_tokens', 'datetime', 'operation',
                      'thread', 'namespace', 'nscanned', 'ntoreturn',
                      'nreturned', 'ninserted', 'nupdated', 'ndeleted',
                      'duration', 'r', 'w', 'numYields',  'cursorid', 'reapedtime',
                      'txtNumber', 'lsid', 'autocommit', 'readConcern',
                      'timeActiveMicros', 'timeInactiveMicros']

        for label in labels:
            value = getattr(self, label, None)
            if value is not None:
                output[label] = value

        return output

    def to_json(self, labels=None):
        """Convert LogEvent object to valid JSON."""
        output = self.to_dict(labels)
        return json.dumps(output, cls=DateTimeEncoder, ensure_ascii=False)

    def _parse_document(self):
        """Parse system.profile doc, copy all values to member variables."""
        self._reset()

        doc = self._profile_doc

        self._split_tokens_calculated = True
        self._split_tokens = None

        self._duration_calculated = True
        self._duration = doc[u'millis']

        self._datetime_calculated = True
        self._datetime = doc[u'ts']
        if self._datetime.tzinfo is None:
            self._datetime = self._datetime.replace(tzinfo=tzutc())
        self._datetime_format = None
        self._reformat_timestamp('ctime', force=True)

        self._thread_calculated = True
        self._thread = doc['thread']

        self._operation_calculated = True
        self._operation = doc[u'op']
        self._namespace = doc[u'ns']

        self._command_calculated = True
        if self.operation == 'command':
            self._command = doc[u'command'].keys()[0]

        # query pattern for system.profile events, all three cases.
        # See SERVER-13245
        if 'query' in doc:
            if 'query' in doc['query'] and isinstance(doc['query']['query'],
                                                      dict):
                self._pattern = str(doc['query']['query']).replace("'", '"')
            elif '$query' in doc['query']:
                self._pattern = str(doc['query']['$query']).replace("'", '"')
            else:
                self._pattern = str(doc['query']).replace("'", '"')

            # sort pattern
            if ('orderby' in doc['query'] and
                    isinstance(doc['query']['orderby'], dict)):
                self._sort_pattern = str(doc['query']
                                         ['orderby']).replace("'", '"')
            elif '$orderby' in doc['query']:
                self._sort_pattern = str(doc['query']
                                         ['$orderby']).replace("'", '"')
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
        self._txnNumber = doc[u'txnNumber'] if 'txnNumber' in doc else None
        self._lsid = doc[u'lsid'] if 'lsid' in doc else None
        self._autocommit = doc[u'autocommit'] if 'autocommit' in doc else None
        self._readConcern = doc[u'level'] if 'level' in doc else None
        self._timeActiveMicros = doc[u'timeActiveMicros'] if 'timeActiveMicros' in doc else None
        self._timeInactiveMicros = doc[u'timeInactiveMicros'] if 'timeInactiveMicros' in doc else None
        self._duration = doc[u'duration'] if 'duration' in doc else None
        self._datetime = doc[u'datetime'] if 'datetime' in doc else None

        if u'lockStats' in doc:
            self._r = doc[u'lockStats'][u'timeLockedMicros'][u'r']
            self._w = doc[u'lockStats'][u'timeLockedMicros'][u'w']
            self._r_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'r']
            self._w_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'w']
            locks = 'w:%i' % self.w if self.w is not None else 'r:%i' % self.r
        elif u'locks' in doc:
            locks = json.dumps(doc[u'locks'])
        else:
            locks = ''

        # build a fake line_str
        payload = ''
        if 'query' in doc:
            payload += ('query: %s' % str(doc[u'query'])
                        .replace("u'", "'").replace("'", '"'))
        if 'command' in doc:
            payload += ('command: %s' % str(doc[u'command'])
                        .replace("u'", "'").replace("'", '"'))
        if 'updateobj' in doc:
            payload += (' update: %s' % str(doc[u'updateobj'])
                        .replace("u'", "'").replace("'", '"'))

        scanned = 'nscanned:%i' % self._nscanned if 'nscanned' in doc else ''
        yields = 'numYields:%i' % self._numYields if 'numYield' in doc else ''
        duration = '%ims' % self.duration if self.duration is not None else ''

        self._line_str = (f'''[{self.thread}] {self.operation} {self.namespace} {payload} '''
                          f'''{scanned} {yields} locks(micros) {locks} '''
                          f'''{duration}''')
