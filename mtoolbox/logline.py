from datetime import datetime
import re
import json

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', \
          'Oct', 'Nov', 'Dec']

class LogLine(object):
    """ LogLine extracts information from a mongod/mongos log file line and 
        stores the following member variables:

        line_str: the original line string
        split_tokens: a list of string tokens after splitting line_str using 
                      whitespace as split points
        datetime: a datetime object for the logline. For logfiles created with 
                  version 2.4+, it also contains micro-seconds
        duration: the duration of a timed operation in ms
        connection: the connection id (e.g. "conn1234") as string
        connection_pos: the token position of the connection
        operation: insert, update, remove, query, command, getmore, None
        namespace: the namespace of the operation, or None
        
        Certain operations also add the number of affected/scanned documents.
        If applicable, the following variables are also set, otherwise the 
        default is None: nscanned, ntoreturn, nreturned, ninserted, nupdated
    """

    def __init__(self, line_str, auto_parse=True):
        # remove line breaks at end of line_str
        self.line_str = line_str.rstrip('\n')

        # datetime handler for json encoding
        self.dthandler = lambda obj: obj.isoformat() if isinstance(obj, \
            datetime) else None

        # split into items (whitespace split)
        self.split_tokens = self.line_str.split()

        if auto_parse:
            self._parse()

    def _parse(self):
        # extract date and time
        self._extract_datetime()
        
        # extract duration from timed operations
        self.duration = None
        if len(self.split_tokens) > 0 and self.split_tokens[-1].endswith('ms'):
            self.duration = int(self.split_tokens[-1][:-2])
        
        # extract connection id (conn####)
        self.connection = None
        for i, item in enumerate(self.split_tokens):
            match = re.match(r'^\[(conn[^\]]*)\]$', item)
            if match:
                self.connection = match.group(1)
                self.connection_pos = i
                break

        # extract operation from connection logs
        self.operation = None
        self.namespace = None
        if self.connection:
            op = self.split_tokens[self.connection_pos+1]
            if op in ['query', 'insert', 'update', 'remove', 'getmore', \
                      'command']:
                self.operation = op
                self.namespace = self.split_tokens[self.connection_pos+2]

                # extract n-values (if present)
                keys = ['nscanned', 'ntoreturn', 'nreturned', 'ninserted', \
                        'nupdated']
                for i in self.split_tokens[self.connection_pos+2:]:
                    for key in keys:
                        if i.startswith('%s:'%key):
                            vars(self)[key] = i.split(':')[-1]
                            break


    def _extract_datetime(self):
        self.datetime = None

        # check if there are enough tokens for datetime
        if len(self.split_tokens) < 4:
            return

        # log file structure: Wed Sep 05 23:02:26 ...
        weekday, month, day, time = self.split_tokens[:4]
        time_match = re.match(r'(\d{2}):(\d{2}):(\d{2})(\.\d{3})?', time)

        # check if it is a valid datetime
        if not (weekday in weekdays and
                month in months and
                re.match(r'\d{1,2}', day) and
                time_match):
            return

        month = months.index(month)+1

        # extract hours, min, sec, millisec from time string
        h, m, s, ms = time_match.groups()

        # old format (pre 2.4) has no ms set to 0
        if ms == None:
            ms = 0
        else:
            ms = int(ms[1:])

        # convert to microsec for datetime
        ms *= 1000

        # TODO: special case if logfile is not from the current year
        year = datetime.now().year

        dt = datetime(int(year), int(month), int(day), int(h), int(m), \
                      int(s), ms)

        self.datetime = dt


    def __str__(self):
        output = ''
        labels = ['datetime', 'operation', 'connection', 'namespace', \
                  'nscanned', 'ntoreturn', 'nreturned', 'duration']
        variables = vars(self)

        for label in labels:
            if not label in variables:
                continue
            output += '%s:'%label
            output += str(variables[label])
            output += " "
        return output


    def to_json(self):
        labels = ['line_str', 'split_tokens', 'datetime', 'operation', \
                  'connection', 'namespace', 'nscanned', 'ntoreturn', \
                  'nreturned', 'duration']
        variables = vars(self)
        output = {}

        for label in labels:
            if (not label in variables) or (variables[label] == None):
                continue
            output[label] = variables[label]

        return json.dumps(output, default=self.dthandler)


