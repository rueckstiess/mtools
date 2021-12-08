import io
import json
import os
import re
import sys
from datetime import datetime, timedelta
from random import randrange

from dateutil import parser
import pytest

import mtools
from mtools.mlogfilter.mlogfilter import MLogFilterTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile


@pytest.fixture(scope="function", autouse=True)
def patch_io(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('my input'))
    sys.stdin.name = 'foo'
    sys.stdin.isatty = lambda: True


def random_date(start, end):
    """Return a random datetime between two datetime objects."""
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogFilter(object):
    """Test functionality around the mlogfilter tool."""

    def setup_method(self):
        """Start up method to create mlaunch tool and find free port."""
        self.tool = MLogFilterTool()

        self._test_base()

    def _test_base(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                         'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))
        self.current_year = datetime.now().year

    def test_msToString(self):
        assert(self.tool._msToString(100) == '0hr 0min 0secs 100ms')
        assert(self.tool._msToString(1000) == '0hr 0min 1secs 0ms')
        assert(self.tool._msToString(100000) == '0hr 1min 40secs 0ms')
        assert(self.tool._msToString(10000000) == '2hr 46min 40secs 0ms')

    def test_from(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from '
                      '%s' % (self.logfile_path,
                              random_start.strftime("%b %d %H:%M:%S.%f")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_iso8601_timestamp(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from %s' % (self.logfile_path,
                                        random_start.isoformat()))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_to(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        random_end = random_date(random_start, self.logfile.end)

        self.tool.run('%s --from %s --to '
                      '%s' % (self.logfile_path,
                              random_start.strftime("%b %d %H:%M:%S.%f"),
                              random_end.strftime("%b %d %H:%M:%S.%f")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start and le.datetime <= random_end)

    def test_from_to_26_log(self):
        logfile_26_path = os.path.join(os.path.dirname(mtools.__file__),
                                       'test/logfiles/', 'mongod_26.log')
        logfile_26 = LogFile(open(logfile_26_path, 'rb'))

        random_start = random_date(logfile_26.start, logfile_26.end)
        random_end = random_date(random_start + timedelta(minutes=1),
                                 logfile_26.end + timedelta(minutes=1))

        print('%s %s' % (random_start, random_end))
        print('%s %s' % (logfile_26.start, logfile_26.end))

        self.tool.run('%s --from %s --to '
                      '%s' % (logfile_26_path,
                              random_start.strftime("%b %d %H:%M:%S.%f"),
                              random_end.strftime("%b %d %H:%M:%S.%f")))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0

        at_least_one = False
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            at_least_one = True
            assert(le.datetime >= random_start and le.datetime <= random_end)
        assert at_least_one

    def test_from_to_stdin(self):

        year = datetime.now().year
        start = datetime(year, 8, 5, 20, 45)
        end = datetime(year, 8, 5, 21, 1)
        self.tool.is_stdin = True
        self.tool.run('%s --from %s --to '
                      '%s' % (self.logfile_path,
                              start.strftime("%b %d %H:%M:%S.%f"),
                              end.strftime("%b %d %H:%M:%S.%f")))
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.datetime >= start and le.datetime <= end)

    def test_json(self):
        """Output with --json is in JSON format."""
        self.tool.run('%s --json' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            line_dict = json.loads(line)
            assert(line_dict)
            assert(type(line_dict) == dict)

    def test_shorten_50(self):
        self.tool.run('%s --shorten 50' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 50)

    def test_shorten_default(self):
        self.tool.run('%s --shorten' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 200)

    def test_merge_same(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s' % (self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 2 * file_length
        for prev, next in zip(lines[:-1], lines[1:]):
            prev_le = LogEvent(prev)
            next_le = LogEvent(next)
            if not prev_le.datetime or not next_le.datetime:
                continue
            assert prev_le.datetime <= next_le.datetime

    def test_merge_markers(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s --markers foo bar' % (self.logfile_path,
                                                   self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len([l for l in lines if l.startswith('foo')]) == file_length
        assert len([l for l in lines if l.startswith('bar')]) == file_length

    def test_merge_invalid_markers(self):
        try:
            self.tool.run('%s %s --markers foo bar baz' % (self.logfile_path,
                                                           self.logfile_path))
        except SystemExit as e:
            assert 'Number of markers not the same' in str(e)

    def test_exclude(self):
        file_length = len(self.logfile)
        tool = MLogFilterTool()
        tool.run('%s --slow 300' % self.logfile_path)

        tool = MLogFilterTool()
        tool.run('%s --slow 300 --exclude' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines_total = len(output.splitlines())

        assert lines_total == file_length

    def test_end_reached(self):
        self.tool.run('%s --from Jan 3015 --to +10min' % self.logfile_path)
        output = sys.stdout.getvalue()
        assert output.strip() == ''

    def test_human(self):
        self.tool.run('%s --slow --thread conn8 --human' % self.logfile_path)
        output = sys.stdout.getvalue().rstrip()
        assert(output.endswith('(0hr 0min 1secs 324ms) 1,324ms'))
        assert('cursorid:7,776,022,515,301,717,602' in output)

    def test_slow_fast(self):
        self.tool.run('%s --slow 145 --fast 500' % self.logfile_path)
        output = sys.stdout.getvalue()
        assert(len(output.splitlines()) > 0)
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.duration >= 145 and le.duration <= 500)

    @pytest.mark.xfail(raises=SystemExit)
    def test_invalid_log(self):
        # load text file
        invalid_logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                            '../', 'requirements.txt')
        self.tool.run('%s' % invalid_logfile_path)

    def test_scan(self):
        # load tablescan logfile
        scn_logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                        'test/logfiles/', 'collscans.log')

        self.tool.run('%s --scan' % scn_logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 3

    def test_accept_nodate(self):
        self.tool.is_stdin = True
        self.tool.run('%s --from Aug 5 %d 20:53:50 --to '
                      '+5min' % (self.logfile_path, self.current_year - 1))
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('=== a line without a datetime ===' in l for l in lines)

    def _test_thread(self, path, thread):
        self.tool.run('%s --thread mongosMain' % path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.thread == thread)
            md = re.match("^.* connection accepted from [0-9\.:]+ "
                          "#(?P<conn>[0-9]+) ", le.line_str)
            if md is None:
                assert(le.conn is None)
            else:
                assert(le.conn == "conn" + md.group('conn'))

    def _test_thread_conn1(self, path, thread):
        self.tool.run('%s --thread conn1' % path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            md = re.match("^.* connection accepted from [0-9\.:]+ "
                          "#(?P<conn>[0-9]+) ", le.line_str)
            assert(le.conn == 'conn1')
            if md is None:
                assert(le.thread == 'conn1')
            else:
                assert(le.thread == thread)

    def test_thread(self):
        self._test_thread(self.logfile_path, 'initandlisten')

    def test_thread_conn1(self):
        self._test_thread_conn1(self.logfile_path, 'initandlisten')

    def test_thread_mongos(self):
        mongos_path = os.path.join(os.path.dirname(mtools.__file__),
                                   'test/logfiles/', 'mongos.log')
        self._test_thread(mongos_path, 'mongosMain')

    def test_thread_mongos_conn1(self):
        mongos_path = os.path.join(os.path.dirname(mtools.__file__),
                                   'test/logfiles/', 'mongos.log')
        self._test_thread_conn1(mongos_path, 'mongosMain')

    def test_no_timestamp_format(self):
        self.tool.run('%s --timestamp-format none --timezone 5'
                      % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if le.datetime:
                assert le.datetime_format == 'ctime-pre2.4'

    def test_operation(self):
        self.tool.run('%s --operation insert' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.operation == 'insert')

    def test_multiple_operations(self):
        self.tool.run('%s --operation insert query' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.operation in ['insert', 'query'])

    def test_invalid_timezone_args(self):
        try:
            self.tool.run('%s --timezone 1 2 3' % self.logfile_path)
        except SystemExit as e:
            assert "Invalid number of timezone parameters" in str(e)

    def test_verbose(self):
        self.tool.run('%s --slow --verbose' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert lines[0].startswith('command line arguments')
        assert any(line.startswith('active filters: SlowFilter')
                   for line in lines)

    def test_namespace(self):
        self.tool.run('%s --namespace local.oplog.rs' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.namespace == 'local.oplog.rs')

    def test_pattern(self):
        # test that pattern is correctly parsed, reordered and compared to
        # logevent pattern
        self.tool.run('%s --pattern {ns:1,_id:1,host:1}' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.pattern == '{"_id": 1, "host": 1, "ns": 1}')

    def test_command(self):
        self.tool.run('%s --command dropDatabase deleteIndexes'
                      % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.command in ['dropDatabase', 'deleteIndexes'])

    def test_planSummary(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26_corrupt.log')
        self.tool.run('%s --planSummary IXSCAN' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert(len(lines) > 0)
        for line in lines:
            le = LogEvent(line)
            assert(le.planSummary == "IXSCAN")

    def test_word(self):
        self.tool.run('%s --word lock' % self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert('lock' in line)

    def test_mask_end(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__),
                                 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size / 2)

        self.tool.run('%s --mask %s --mask-size %i' % (self.logfile_path,
                                                       mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert((le.datetime >= event1 - padding and
                    le.datetime <= event1 + padding) or
                   (le.datetime >= event2 - padding and
                    le.datetime <= event2 + padding))

    def test_mask_start(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__),
                                 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size / 2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center start'
                      % (self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert((le.datetime >= event1 - duration1 - padding and
                    le.datetime <= event1 - duration1 + padding) or
                   (le.datetime >= event2 - padding and
                    le.datetime <= event2 + padding))

    def test_mask_both(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__),
                                 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size / 2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center both'
                      % (self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert((le.datetime >= event1 - duration1 - padding and
                    le.datetime <= event1 + padding) or
                   (le.datetime >= event2 - padding and
                    le.datetime <= event2 + padding))

    @pytest.mark.xfail(raises=SystemExit)
    def test_no_logfile(self):
        """Test that not providing at least 1 log file throws clean error."""

        self.tool.run('--from Jan 1')

    def test_year_rollover_1(self):
        """
        Test that mlogfilter works correctly with year-rollovers in logfiles
        with ctime (1).
        """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                        'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Jan 1 %d --timestamp-format iso8601-utc'
                      % (yro_logfile_path, self.current_year))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert line.startswith('%d-' % self.current_year)

    def test_year_rollover_2(self):
        """
        Test that mlogfilter works correctly with year-rollovers in logfiles
        with ctime (2).
        """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                        'test/logfiles/', 'year_rollover.log')
        self.tool.run('%s --from Dec 31 --to +1day --timestamp-format '
                      'iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0
        for line in output.splitlines():
            assert line.startswith('%d-' % (self.current_year - 1))

    def test_level_225(self):
        """Test that mlogfilter works levels on older logs."""

        self.tool.run('%s --level D ' % self.logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) == 0

    def test_component_225(self):
        """Test that mlogfilter works components on older logs."""

        self.tool.run('%s --component ACCESS ' % self.logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) == 0

    @pytest.mark.xfail(raises=SystemExit)
    def test_invalid_level(self):
        self._test_base('mongod_278.log')
        self.tool.run(' %s --level C' % self.logfile_path)

    @pytest.mark.xfail(raises=SystemExit)
    def test_invalid_component(self):
        self._test_base('mongod_278.log')
        self.tool.run(' %s --component FAKE' % self.logfile_path)

    def _test_levels(self, level, expected=1):
        self._test_base('mongod_278.log')
        self.tool.run(' %s --level %s' % (self.logfile_path, level))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) == expected

    def _test_components(self, component, expected=1):
        self._test_base('mongod_278.log')
        self.tool.run(' %s --component %s' % (self.logfile_path, component))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) == expected


def _add_component_test(cls, name, component, expected):
    """Meta program new tests."""
    def test_method(self):
        self._test_components(component, expected)
    test_method.__doc__ = name
    test_method.__name__ = name
    setattr(cls, test_method.__name__, test_method)


_add_component_test(TestMLogFilter, 'test_total_component', 'TOTAL', 1)
_add_component_test(TestMLogFilter, 'test_s2_component', 'GEO', 1)
_add_component_test(TestMLogFilter, 'test_all_component',
                    " ".join(LogEvent.log_components), 25)
_add_component_test(TestMLogFilter, 'test_dash_component', '-', 10)
_add_component_test(TestMLogFilter, 'test_access_component', 'ACCESS', 1)
_add_component_test(TestMLogFilter, 'test_commands_component', 'COMMAND', 1)
_add_component_test(TestMLogFilter, 'test_indexing_component', 'INDEX', 1)
_add_component_test(TestMLogFilter, 'test_network_component', 'NETWORK', 1)
_add_component_test(TestMLogFilter, 'test_query_component', 'QUERY', 1)
_add_component_test(TestMLogFilter, 'test_replsets_component', 'REPL', 1)
_add_component_test(TestMLogFilter, 'test_sharding_component', 'SHARDING', 1)
_add_component_test(TestMLogFilter, 'test_storage_component', 'STORAGE', 4)
_add_component_test(TestMLogFilter, 'test_journal_component', 'JOURNAL', 1)
_add_component_test(TestMLogFilter, 'test_writes_component', 'WRITE', 1)


def _add_level_test(cls, name, level, expected=1):
    """
    meta program new tests
    """
    def test_method(self):
        self._test_levels(level, expected)
    test_method.__doc__ = name
    test_method.__name__ = name
    setattr(cls, test_method.__name__, test_method)


_add_level_test(TestMLogFilter, 'test_all_levels',
                " ".join(LogEvent.log_levels), 25)
_add_level_test(TestMLogFilter, 'test_D_levels', 'D')
_add_level_test(TestMLogFilter, 'test_F_levels', 'F')
_add_level_test(TestMLogFilter, 'test_E_levels', 'E')
_add_level_test(TestMLogFilter, 'test_W_levels', 'W')
_add_level_test(TestMLogFilter, 'test_I_levels', 'I', 20)
_add_level_test(TestMLogFilter, 'test_U_levels', 'U')

# output = sys.stdout.getvalue().strip()
