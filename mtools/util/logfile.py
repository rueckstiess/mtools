#!/usr/bin/env python3

import os
import re
import sys
from datetime import datetime
from math import ceil

from mtools.util.input_source import InputSource
from mtools.util.logevent import LogEvent
from mtools.util.logfile_metadata import MetadataMixin
from mtools.util.logfile_sharding import ShardingInfoMixin
from mtools.util.logformat import LogFormat

# Legacy records open with the same shapes LogEvent accepts at column 0.
_ISO8601_RECORD_RE = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}')
_CTIME_RECORD_RE = re.compile(
    r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+'
    r'\d{1,2}\s+\d{2}:\d{2}:\d{2}')


def _is_legacy_record(line):
    """True when a physical line opens an ISO-8601 or ctime record."""
    if _ISO8601_RECORD_RE.match(line):
        return True
    return _CTIME_RECORD_RE.match(line) is not None


def _is_record_start(line):
    """True when a physical line opens a legacy or structured record."""
    if not line:
        return False
    if line.startswith('{'):
        return True
    return _is_legacy_record(line)


def _has_duration_suffix(line):
    """True when a line ends in the timed-operation ``<digits>ms`` form."""
    line = line.rstrip()
    if not line.endswith('ms'):
        return False
    if 'Scheduled new oplog query' in line:
        return False
    tail = line[line.rfind(' ') + 1:-2].replace(',', '')
    return tail.isdigit()


class LogFile(MetadataMixin, ShardingInfoMixin, InputSource):
    """Log file wrapper class. Handles open file streams or stdin."""

    def __init__(self, filehandle):
        """Provide logfile as open file stream or stdin."""
        self.filehandle = filehandle
        self.name = filehandle.name
        self.from_stdin = filehandle.name == "<stdin>"

        self._logformat = None
        self._bounds_calculated = False
        self._start = None
        self._end = None
        self._filesize = None
        self._num_lines = None
        self._restarts = None
        self._binary = None
        self._clusterrole = None
        self._timezone = None
        self._hostname = None
        self._port = None
        self._rs_state = None

        self._repl_set = None
        self._repl_set_members = None
        self._repl_set_version = None
        self._repl_set_protocol = None

        self._storage_engine = None

        self._datetime_format = None
        self._year_rollover = None

        self._shards = None
        self._csrs = None

        self._chunks_moved_from = None
        self._chunks_moved_to = None
        self._chunk_splits = None

        # Track previous file position for loop detection in _find_curr_line()
        self.prev_pos = None
        # Events read ahead of iteration, replayed by next().
        self._readahead = []
        # Lines returned by next(), counted from the start of this read.
        self._lines_read = 0
        # One physical line held for stdin, which cannot seek back.
        self._pending_line = None

        self._has_level = None

        # make sure bounds are calculated before starting to iterate,
        # including potential year rollovers
        self._calculate_bounds()

    def __getstate__(self):
        """
        Return state values to be pickled.
        """
        if (self.name != '<stdin>'):
            return (self.name)
        else:
            return ()

    def __setstate__(self, state):
        """
        Restore state from the unpickled state values.
        """
        self.name = state

    @property
    def logformat(self):
        """
        Determine type of logfile: LEGACY, LOGV2, PROFILE
        """
        if not self._logformat:
            self._calculate_bounds()
        return self._logformat

    @property
    def start(self):
        """
        Lazy evaluation of start and end of logfile.

        Returns None for stdin input currently.
        """
        if not self._start:
            self._calculate_bounds()
        return self._start

    @property
    def end(self):
        """
        Lazy evaluation of start and end of logfile.

        Returns None for stdin input currently.
        """
        if not self._end:
            self._calculate_bounds()
        return self._end

    @property
    def timezone(self):
        """Lazy evaluation of timezone of logfile."""
        if not self._timezone:
            self._calculate_bounds()
        return self._timezone

    @property
    def filesize(self):
        """
        Lazy evaluation of start and end of logfile.

        Returns None for stdin input currently.
        """
        if self.from_stdin:
            return None
        if not self._filesize:
            self._calculate_bounds()
        return self._filesize

    @property
    def datetime_format(self):
        """Lazy evaluation of the datetime format."""
        if not self._datetime_format:
            self._calculate_bounds()
        return self._datetime_format

    @property
    def has_level(self):
        """Lazy evaluation of the whether the logfile has any level lines."""
        if self._has_level is None:
            self._iterate_lines()

        return self._has_level

    @property
    def year_rollover(self):
        """Lazy evaluation of the datetime format."""
        if self._year_rollover is None:
            self._calculate_bounds()
        return self._year_rollover

    @property
    def num_lines(self):
        """Number of log records. Stdin returns None.

        Physical lines that wrap inside one query count as one record.
        """
        if self.from_stdin:
            return None
        if self._num_lines is None:
            self._iterate_lines()
        return self._num_lines

    @property
    def restarts(self):
        """Lazy evaluation of all restarts."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._restarts

    @property
    def rs_state(self):
        """Lazy evaluation of all restarts."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._rs_state

    @property
    def binary(self):
        """Lazy evaluation of the binary name."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._binary

    @property
    def clusterrole(self):
        """Lazy evaluation of the clusterRole."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._clusterrole

    @property
    def hostname(self):
        """Lazy evaluation of the binary name."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._hostname

    @property
    def port(self):
        """Lazy evaluation of the binary name."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._port

    @property
    def versions(self):
        """Return all version changes."""
        versions = []
        for v, _ in self.restarts:
            if len(versions) == 0 or v != versions[-1]:
                versions.append(v)
        return versions

    @property
    def repl_set(self):
        """Return the replSet (if available)."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._repl_set

    @property
    def repl_set_members(self):
        """Return the replSet (if available)."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._repl_set_members

    @property
    def repl_set_version(self):
        """Return the replSet (if available)."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._repl_set_version

    @property
    def repl_set_protocol(self):
        """Return the replSet protocolVersion (if available)."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._repl_set_protocol

    @property
    def storage_engine(self):
        """Return storage engine if available."""
        if self._num_lines is None:
            self._iterate_lines()
        return self._storage_engine

    @property
    def shards(self):
        """Lazily return the shards (if available)"""
        if not self._shards:
            self._find_sharding_info()
        return self._shards

    @property
    def csrs(self):
        """Lazily return the CSRS (if available)"""
        if not self._csrs:
            self._find_sharding_info()
        return self._csrs

    @property
    def chunks_moved_to(self):
        """Lazily return the chunks moved to this shard (if available)"""
        if not self._chunks_moved_to:
            self._find_sharding_info()
        return self._chunks_moved_to

    @property
    def chunks_moved_from(self):
        """Lazily return the chunks moved from this shard (if available)"""
        if not self._chunks_moved_from:
            self._find_sharding_info()
        return self._chunks_moved_from

    @property
    def chunk_splits(self):
        """Lazily return the chunks split in this shard (if available)"""
        if not self._chunk_splits:
            self._find_sharding_info()
        return self._chunk_splits

    def _seek(self, offset, whence=0):
        """Move the file position and drop a held stdin line."""
        self._pending_line = None
        self.filehandle.seek(offset, whence)

    def _readline(self):
        """Read one physical line. None means EOF.

        readline() keeps the seek position accurate. Iterating the file
        object buffers ahead of that position.
        """
        line = self.filehandle.readline()
        if isinstance(line, bytes):
            line = line.decode('utf-8', 'replace')
        if line == '':
            return None
        return line.rstrip('\r\n')

    def _next_physical_line(self):
        if self._pending_line is not None:
            line = self._pending_line
            self._pending_line = None
            return line
        return self._readline()

    def _peek_physical_line(self):
        """Look at the next physical line and leave it to be read again."""
        if self._pending_line is not None:
            return self._pending_line
        if self.from_stdin:
            self._pending_line = self._readline()
            return self._pending_line
        pos = self.filehandle.tell()
        line = self._readline()
        if line is not None:
            self._seek(pos)
        return line

    def _read_record(self):
        """Return the next log record, or None at EOF.

        A query can contain a newline, so one record may span physical
        lines. Lines that follow a legacy timestamp belong to that
        record until the next timestamp. A structured log line starts
        with ``{`` and stays a single line. Once a legacy record ends in
        a duration suffix such as ``129ms``, a later non-timestamp line
        is skipped so a banner cannot remove that duration.
        """
        line = self._next_physical_line()
        while line is not None and not _is_record_start(line):
            line = self._next_physical_line()
        if line is None:
            return None
        if line.startswith('{'):
            return line

        parts = [line]
        while True:
            nxt = self._peek_physical_line()
            if nxt is None or _is_legacy_record(nxt):
                break
            if _has_duration_suffix(parts[-1]):
                # the record is complete; leftover lines are skipped by
                # the next read
                break
            parts.append(self._next_physical_line())
        return ' '.join(parts)

    def next(self):
        """Get next record, adjust for year rollover and hint datetime format."""
        if self._readahead:
            return self._readahead.pop(0)

        offset = self.filehandle.tell() if self._lines_read is None else None
        line = self._read_record()
        if line is None:
            raise StopIteration
        if self._lines_read is not None:
            self._lines_read += 1
            location = "%s line %i" % (self.name, self._lines_read)
        else:
            location = "%s byte offset %i" % (self.name, offset)
        try:
            le = LogEvent(line)

            # hint format and nextpos from previous line
            if self._datetime_format and self._datetime_nextpos is not None:
                ret = le.set_datetime_hint(self._datetime_format,
                                           self._datetime_nextpos,
                                           self.year_rollover)
                if not ret:
                    # logevent indicates timestamp format has changed,
                    # invalidate hint info
                    self._datetime_format = None
                    self._datetime_nextpos = None
            elif le.datetime:
                # gather new hint info from another logevent
                self._datetime_format = le.datetime_format
                self._datetime_nextpos = le._datetime_nextpos
        except StopIteration:
            raise
        except Exception as exc:
            self._report_parse_error(line, exc, location)
            raise

        return le

    def timezone_from_stream(self, limit=10):
        """Return the first timestamp's zone, then replay the lines read.

        Stdin cannot be scanned from both ends the way a file can. The
        lines read here are returned again by next(), in order.
        """
        saved = []
        found = None
        for _ in range(limit):
            try:
                logevent = self.next()
            except StopIteration:
                break
            saved.append(logevent)
            if logevent.datetime is not None and logevent.datetime.tzinfo:
                found = logevent.datetime.tzinfo
                self._stream_start = logevent
                break
        self._readahead = saved + self._readahead
        return found

    def first_dated_from_stream(self):
        """First timestamp seen by timezone_from_stream(), if it has a year.

        Only ISO 8601 timestamps carry a year. A ctime timestamp gets the
        current year, which is a guess, so it is not returned.
        """
        logevent = getattr(self, '_stream_start', None)
        if logevent is None:
            return None
        if not (logevent.datetime_format or '').startswith('iso8601'):
            return None
        return logevent.datetime

    def __iter__(self):
        """
        Iterate over LogFile object.

        Return a LogEvent object for each line (generator).
        """
        le = None

        while True:
            try:
                le = self.next()
            except StopIteration:
                # end of log file, get end date
                if not self.end and self.from_stdin:
                    if le and le.datetime:
                        self._end = le.datetime

                # future iterations start from the beginning
                if not self.from_stdin:
                    self._seek(0)
                    self._lines_read = 0

                # return (instead of raising StopIteration exception) per PEP 479
                return

            # get start date for stdin input
            if not self.start and self.from_stdin:
                if le and le.datetime:
                    self._start = le.datetime

            try:
                yield le
            except StopIteration:
                return

    states = (['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2',
               'RECOVERING', 'ROLLBACK', 'ARBITER', 'UNKNOWN'])

    def __len__(self):
        """Return the number of log records in a log file."""
        return self.num_lines

    def _iterate_lines(self):
        """Count log records and collect metadata. Can be expensive."""
        self._num_lines = 0
        self._restarts = []
        self._rs_state = []
        self._pending_line = None

        count = 0
        while True:
            record = self._read_record()
            if record is None:
                break
            count += 1
            if self.logformat == LogFormat.LOGV2:
                self._extract_metadata_logv2(record)
            else:
                self._extract_metadata_legacy(record)

        self._num_lines = count

        # reset logfile
        self._seek(0)
        self._lines_read = 0

    def _calculate_bounds(self):
        """Calculate beginning and end of logfile."""
        if self._bounds_calculated:
            # Assume no need to recalc bounds for lifetime of a Logfile object
            return

        if self.from_stdin:
            return False

        # we should be able to find a valid log line within max_start_lines
        max_start_lines = 10
        lines_checked = 0

        # get start datetime
        for line in self.filehandle:
            lines_checked += 1
            # LogEvent will determine the LogFormat
            # datetime is parsed lazily, so read it inside the try
            try:
                logevent = LogEvent(line)
                when = logevent.datetime
            except Exception as exc:
                self._report_parse_error(
                    line, exc, "%s line %i" % (self.name, lines_checked))
                raise

            if when:
                self._start = logevent.datetime
                self._timezone = logevent.datetime.tzinfo
                self._datetime_format = logevent.datetime_format
                self._datetime_nextpos = logevent._datetime_nextpos
                self._logformat = logevent.logformat
                break
            if lines_checked >= max_start_lines:
                break

        # sanity check before attempting to find end date
        if (self._logformat is None):
            raise SystemExit("Error: <%s> does not appear to be a supported "
                             "MongoDB log file format" % self.filehandle.name)

        # get end datetime (lines are at most 10k,
        # go back 30k at most to make sure we catch one)
        self._seek(0, 2)
        self._filesize = self.filehandle.tell()
        self._seek(-min(self._filesize, 30000), 2)

        for line in reversed(self.filehandle.readlines()):
            try:
                logevent = LogEvent(line)
                when = logevent.datetime
            except Exception as exc:
                self._report_parse_error(
                    line, exc, "%s near the end" % self.name)
                raise
            if when:
                self._end = logevent.datetime
                break

        # if there was a roll-over, subtract 1 year from start time
        if self._end < self._start:
            self._start = self._start.replace(year=self._start.year - 1)
            self._year_rollover = self._end
        else:
            self._year_rollover = False

        # reset logfile
        self._seek(0)
        self._lines_read = 0
        self._bounds_calculated = True

        return True

    def _report_parse_error(self, line, exc, location):
        """Print the log line that failed to parse.

        The caller re-raises. Skipping the line would drop events with
        no signal that the log was incomplete.
        """
        if isinstance(line, bytes):
            text = line.decode('utf-8', 'replace')
        else:
            text = line
        text = text.rstrip('\r\n')
        if len(text) > 500:
            text = text[:500] + '...'
        print("Error parsing %s: %s\n%s" % (location, exc, text),
              file=sys.stderr)

    def _prev_record_newline(self, buff, jump_back, curr_pos):
        """Index in buff of the newline before the previous record.

        A record can span several physical lines, so stepping back one line
        can land inside the record we are already on. Walk back over lines
        until we pass the start of the current record and reach the start of
        the one before it. Returns -1 when that is not inside buff.
        """
        newline = b'\n' if isinstance(buff, bytes) else '\n'
        # read the rest of the line at curr_pos so it can be tested whole
        self._seek(curr_pos, 0)
        tail = self.filehandle.readline()
        self._seek(curr_pos, 0)
        text = buff + tail
        found = 0
        pos = jump_back
        while True:
            nl = text.rfind(newline, 0, pos)
            if nl == -1:
                return -1
            end = text.find(newline, nl + 1)
            line = text[nl + 1:] if end == -1 else text[nl + 1:end]
            if isinstance(line, bytes):
                line = line.decode('utf-8', 'replace')
            if _is_record_start(line.rstrip('\r')):
                found += 1
                if found == 2:
                    return nl
            pos = nl

    def _find_curr_line(self, prev=False):
        """
        Internal helper function.

        Find the current (or previous if prev=True) line in a log file based on
        the current seek position.
        """
        curr_pos = self.filehandle.tell()

        # jump back 15k characters (at most) and find last newline char
        jump_back = min(self.filehandle.tell(), 15000)
        self._seek(-jump_back, 1)
        buff = self.filehandle.read(jump_back)
        self._seek(curr_pos, 0)

        if prev and self.prev_pos is not None and self.prev_pos == curr_pos:
            # Number of characters to show before/after the log offset
            error_context = 300
            self._seek(-error_context, 1)
            buff = self.filehandle.read(curr_pos)
            hr = "-" * 60
            print("Fatal log parsing loop detected trying to find previous "
                  "log line near offset %s in %s:\n\n%s\n%s\n"
                  "<--- (current log parsing offset) \n%s\n%s\n"
                  % (curr_pos, self.name, hr, buff[:error_context],
                     buff[error_context:error_context + 1], hr),
                  file=sys.stderr)
            raise SystemExit("Cannot parse %s with requested options"
                             % self.filehandle.name)
        else:
            self.prev_pos = curr_pos

        if prev:
            newline_pos = self._prev_record_newline(buff, jump_back, curr_pos)
        else:
            if isinstance(buff, bytes):
                buff = buff.decode("utf-8", "replace")
            newline_pos = buff.rfind('\n')

        # move back to last newline char
        if newline_pos == -1:
            self._seek(0)
            self._lines_read = 0
            return self.next()

        self._seek(newline_pos - jump_back + 1, 1)

        # line count is unknown after a relative seek

        self._lines_read = None

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
        """
        Fast-forward file to given start_dt datetime obj using binary search.

        Only fast for files. Streams need to be forwarded manually, and it will
        miss the first line that would otherwise match (as it consumes the log
        line).
        """
        if self.from_stdin:
            # skip lines until start_dt is reached
            return

        else:
            # fast bisection path
            max_mark = self.filesize
            step_size = max_mark

            # check if start_dt is already smaller than first datetime
            self._seek(0)
            self._lines_read = 0
            le = self.next()
            if le.datetime and le.datetime >= start_dt:
                self._seek(0)
                self._lines_read = 0
                return

            le = None
            self._seek(0)
            self._lines_read = 0

            # search for lower bound
            while abs(step_size) > 100:
                step_size = ceil(step_size / 2.)

                self._seek(step_size, 1)

                # line count is unknown after a relative seek

                self._lines_read = None
                le = self._find_curr_line()
                if not le:
                    break

                if le.datetime >= start_dt:
                    step_size = -abs(step_size)
                else:
                    step_size = abs(step_size)

            if not le:
                return

            # now walk backwards until we found a truly smaller line
            while self.filehandle.tell() >= 2 and (le.datetime is None or
                                                   le.datetime >= start_dt):
                self._seek(-2, 1)
                # line count is unknown after a relative seek
                self._lines_read = None

                le = self._find_curr_line(prev=True)
