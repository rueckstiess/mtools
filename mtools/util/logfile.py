from mtools.util.logevent import LogEvent
from mtools.util.input_source import InputSource

from math import ceil 
from datetime import datetime
import time
import re
import os

class LogFile(InputSource):
    """ wrapper class for log files, either as open file streams of from stdin. """

    def __init__(self, filehandle):
        """ provide logfile as open file stream or stdin. """
        self.filehandle = filehandle
        self.name = filehandle.name
        
        self.from_stdin = filehandle.name == "<stdin>"
        self._start = None
        self._end = None
        self._filesize = None
        self._num_lines = None
        self._restarts = None
        self._binary = None
        self._timezone = None
        self._hostname = None
        self._port = None
        self._rs_state = None

        self._repl_set = None
        self._repl_set_members = None
        self._repl_set_version = None
        
        self._storage_engine = None
        
        self._datetime_format = None
        self._year_rollover = None

        self._has_level= None
        
        # make sure bounds are calculated before starting to iterate, including potential year rollovers
        self._calculate_bounds()

    @property
    def start(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if not self._start:
            self._calculate_bounds()
        return self._start

    @property
    def end(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if not self._end:
            self._calculate_bounds()
        return self._end

    @property
    def timezone(self):
        """ lazy evaluation of timezone of logfile. """
        if not self._timezone:
            self._calculate_bounds()
        return self._timezone

    @property
    def filesize(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._filesize:
            self._calculate_bounds()
        return self._filesize

    @property
    def datetime_format(self):
        """ lazy evaluation of the datetime format. """
        if not self._datetime_format:
            self._calculate_bounds()
        return self._datetime_format

    @property
    def has_level(self):
        """ lazy evaluation of the whether the logfile has any level lines. """
        if self._has_level is None:
            self._iterate_lines()
        return self._has_level

    @property
    def year_rollover(self):
        """ lazy evaluation of the datetime format. """
        if self._year_rollover == None:
            self._calculate_bounds()
        return self._year_rollover

    @property
    def num_lines(self):
        """ lazy evaluation of the number of lines. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._num_lines:
            self._iterate_lines()
        return self._num_lines

    @property
    def restarts(self):
        """ lazy evaluation of all restarts. """
        if not self._num_lines:
            self._iterate_lines()
        return self._restarts

    @property
    def rs_state(self):
        """ lazy evaluation of all restarts. """
        if not self._num_lines:
            self._iterate_lines()
        return self._rs_state

    @property
    def binary(self):
        """ lazy evaluation of the binary name. """
        if not self._num_lines:
            self._iterate_lines()
        return self._binary

    @property
    def hostname(self):
        """ lazy evaluation of the binary name. """
        if not self._num_lines:
            self._iterate_lines()
        return self._hostname

    @property
    def port(self):
        """ lazy evaluation of the binary name. """
        if not self._num_lines:
            self._iterate_lines()
        return self._port

    @property
    def versions(self):
        """ return all version changes. """
        versions = []
        for v, _ in self.restarts:
            if len(versions) == 0 or v != versions[-1]:
                versions.append(v)
        return versions

    @property
    def repl_set(self):
        """ return the replSet (if available). """
        if not self._num_lines:
            self._iterate_lines()
        return self._repl_set

    @property
    def repl_set_members(self):
        """ return the replSet (if available). """
        if not self._num_lines:
            self._iterate_lines()
        return self._repl_set_members

    @property
    def repl_set_version(self):
        """ return the replSet (if available). """
        if not self._num_lines:
            self._iterate_lines()
        return self._repl_set_version

    @property
    def storage_engine(self):
        """ return storage engine if available """
        if not self._num_lines:
            self._iterate_lines()
        return self._storage_engine
    

    def next(self):
        """ get next line, adjust for year rollover and hint datetime format. """

        # use readline here because next() iterator uses internal readahead buffer so seek position is wrong
        line = self.filehandle.readline()
        line = line.rstrip('\n')

        if line == '':
            raise StopIteration

        le = LogEvent(line)
        
        # hint format and nextpos from previous line
        if self._datetime_format and self._datetime_nextpos != None:
            ret = le.set_datetime_hint(self._datetime_format, self._datetime_nextpos, self.year_rollover)
            if not ret:
                # logevent indicates timestamp format has changed, invalidate hint info
                self._datetime_format = None
                self._datetime_nextpos = None
        elif le.datetime:
            # gather new hint info from another logevent
            self._datetime_format = le.datetime_format
            self._datetime_nextpos = le._datetime_nextpos  

        return le

    def __iter__(self):
        """ iteration over LogFile object will return a LogEvent object for each line (generator) """
        le = None
        
        while True:
            try:
                le = self.next()
            except StopIteration as e:
                # end of log file, get end date
                if not self.end and self.from_stdin:
                    if le and le.datetime:
                        self._end = le.datetime

                # future iterations start from the beginning
                if not self.from_stdin:
                    self.filehandle.seek(0)
                
                # now raise StopIteration exception
                raise e

            # get start date for stdin input
            if not self.start and self.from_stdin:
                if le and le.datetime:
                    self._start = le.datetime

            yield le

    states = ['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2', 'RECOVERING', 'ROLLBACK', 'ARBITER', 'UNKNOWN']

    def __len__(self):
        """ return the number of lines in a log file. """
        return self.num_lines


    def _iterate_lines(self):
        """ count number of lines (can be expensive). """
        self._num_lines = 0
        self._restarts = []
        self._rs_state = []

        l = 0
        for l, line in enumerate(self.filehandle):

            if self._has_level is None and line[28:31].strip() in LogEvent.log_levels and line[31:39].strip() in LogEvent.log_components:
                self._has_level = True

            # find version string (fast check to eliminate most lines)
            if "version" in line[:100]:
                logevent = LogEvent(line)
                restart = self._check_for_restart(logevent)
                if restart:
                    self._restarts.append((restart, logevent))

            if "starting :" in line or "starting:" in line:
                # look for hostname, port
                match = re.search('port=(?P<port>\d+).*host=(?P<host>\S+)', line)
                if match:
                    self._hostname = match.group('host')
                    self._port = match.group('port')

            ''' For 3.0 the "[initandlisten] options:" long entry contained the "engine" field
                if WiredTiger was the storage engine. There were only two engines, MMAPv1
                and WiredTiger
            '''
            if "[initandlisten] options:" in line:
                match = re.search('replSet: "(?P<replSet>\S+)"', line)
                if match:
                    self._repl_set = match.group('replSet')

                match = re.search('engine: "(?P<engine>\S+)"', line)
                if match:
                    self._storage_engine = match.group('engine')
                else:
                    self._storage_engine = 'mmapv1'

            ''' For 3.2 the "[initandlisten] options:" no longer contains the "engine" field
                So now we have to look for the "[initandlisten] wiredtiger_open config:"
                which was present in 3.0, but would now tell us definatively that wiredTiger is being used
            '''
            if "[initandlisten] wiredtiger_open config:" in line:
                self._storage_engine =  'wiredTiger'

            if "command admin.$cmd command: { replSetInitiate:" in line:
                match = re.search('{ _id: "(?P<replSet>\S+)", members: (?P<replSetMembers>[^]]+ ])', line)
                if match:
                    self._repl_set = match.group('replSet')
                    self._repl_set_members = match.group('replSetMembers')

            if "replSet info saving a newer config version to local.system.replset: " in line:
                match = re.search('{ _id: "(?P<replSet>\S+)", version: (?P<replSetVersion>\d+), members: (?P<replSetMembers>[^]]+ ])', line)
                if match:
                    self._repl_set = match.group('replSet')
                    self._repl_set_members = match.group('replSetMembers')
                    self._repl_set_version = match.group('replSetVersion')
    
            # if "is now in state" in line and next(state for state in states if line.endswith(state)):
            if "is now in state" in line:
                tokens = line.split()
                # 2.6
                if tokens[1].endswith(']'):
                    pos = 4
                else:
                    pos = 5
                host = tokens[pos]
                rs_state = tokens[-1]
                state = (host, rs_state, LogEvent(line))
                self._rs_state.append(state)
                continue

            if "[rsMgr] replSet" in line:
                tokens = line.split()
                if self._hostname:
                    host = self._hostname + ':' + self._port 
                else:
                    host = os.path.basename(self.name)
                host += ' (self)'
                if tokens[-1] in self.states:
                    rs_state = tokens[-1]
                else:
                    # 2.6
                    if tokens[1].endswith(']'):
                        pos = 2
                    else:
                        pos = 6
                    rs_state = ' '.join(tokens[pos:])

                state = (host, rs_state, LogEvent(line))
                self._rs_state.append(state)
                continue


        self._num_lines = l+1

        # reset logfile
        self.filehandle.seek(0)


    def _check_for_restart(self, logevent):
        if logevent.thread == 'mongosMain' and 'MongoS' in logevent.line_str:
            self._binary = 'mongos'
        
        elif logevent.thread == 'initandlisten' and "db version v" in logevent.line_str:
            self._binary = 'mongod'

        else:
            return False

        version = re.search(r'(\d\.\d\.\d+)', logevent.line_str)
                
        if version:
            version = version.group(1)
            return version
        else:
            return False


    def _calculate_bounds(self):
        """ calculate beginning and end of logfile. """

        if self.from_stdin: 
            return False

        # get start datetime 
        for line in self.filehandle:
            logevent = LogEvent(line)
            if logevent.datetime:
                self._start = logevent.datetime
                self._timezone = logevent.datetime.tzinfo
                self._datetime_format = logevent.datetime_format
                self._datetime_nextpos = logevent._datetime_nextpos
                break

        # get end datetime (lines are at most 10k, go back 30k at most to make sure we catch one)
        self.filehandle.seek(0, 2)
        self._filesize = self.filehandle.tell()
        self.filehandle.seek(-min(self._filesize, 30000), 2)

        for line in reversed(self.filehandle.readlines()):
            logevent = LogEvent(line)
            if logevent.datetime:
                self._end = logevent.datetime
                break

        # if there was a roll-over, subtract 1 year from start time
        if self._end < self._start:
            self._start = self._start.replace(year=self._start.year-1)
            self._year_rollover = self._end
        else:
            self._year_rollover = False

        # reset logfile
        self.filehandle.seek(0)

        return True


    def _find_curr_line(self, prev=False):
        """ internal helper function that finds the current (or previous if prev=True) line in a log file
            based on the current seek position.
        """
        curr_pos = self.filehandle.tell()
        line = None

        # jump back 15k characters (at most) and find last newline char
        jump_back = min(self.filehandle.tell(), 15000)
        self.filehandle.seek(-jump_back, 1)
        buff = self.filehandle.read(jump_back)
        self.filehandle.seek(curr_pos, 0)

        newline_pos = buff.rfind('\n')
        if prev:
            newline_pos = buff[:newline_pos].rfind('\n')

        # move back to last newline char
        if newline_pos == -1:
            self.filehandle.seek(0)
            return self.next()

        self.filehandle.seek(newline_pos - jump_back + 1, 1)

        # roll forward until we found a line with a datetime
        try:
            logevent = self.next()
            while not logevent.datetime:
                logevent = self.next()

            return logevent
        except StopIteration:
            # reached end of file
            return None


    def fast_forward(self, start_dt):
        """ Fast-forward a log file to the given start_dt datetime object using binary search.
            Only fast for files. Streams need to be forwarded manually, and it will miss the 
            first line that would otherwise match (as it consumes the log line). 
        """
        if self.from_stdin:
            # skip lines until start_dt is reached
            return

        else:
            # fast bisection path
            min_mark = 0
            max_mark = self.filesize
            step_size = max_mark

            # check if start_dt is already smaller than first datetime
            self.filehandle.seek(0)
            le = self.next()
            if le.datetime and le.datetime >= start_dt:
                self.filehandle.seek(0)
                return

            le = None
            self.filehandle.seek(0)

            # search for lower bound
            while abs(step_size) > 100:
                step_size = ceil(step_size / 2.)
                
                self.filehandle.seek(step_size, 1)
                le = self._find_curr_line()
                if not le:
                    break
                                
                if le.datetime >= start_dt:
                    step_size = -abs(step_size)
                else:
                    step_size = abs(step_size)

            if not le:
                return

            # now walk backwards until we found a truely smaller line
            while le and self.filehandle.tell() >= 2 and le.datetime >= start_dt:
                self.filehandle.seek(-2, 1)
                le = self._find_curr_line(prev=True)



