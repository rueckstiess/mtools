from mtools.mlogfilter.mlogfilter import MLogFilterTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile
import mtools

from nose.tools import *
from nose.plugins.skip import Skip, SkipTest

from random import randrange
from datetime import timedelta, datetime
from dateutil import parser
import os
import sys
import re
import json


def random_date(start, end):
    """ This function will return a random datetime between two datetime objects. """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogFilter(object):
    """ This class tests functionality around the mlogfilter tool. """

    def setup(self):
        """ start up method to create mlaunch tool and find free port. """
        self.tool = MLogFilterTool()

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_225.log')
        self.logfile = LogFile(open(self.logfile_path, 'r'))


    def _test_from_to_line(self, frm, to, first, last, path='test-mlogfilter-issue-50.log'):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', path)
        self.logfile = LogFile(open(self.logfile_path, 'r'))

        args = ""
        if frm:
            args = " %s --from %s " % (args , parser.parse(frm).isoformat())
        if to:
            args = " %s --to %s " % (args , parser.parse(to).isoformat())


        self.tool.run('%s %s'%(self.logfile_path, args))
        output = sys.stdout.getvalue()

        lines = output.splitlines()
        if first:
            assert(lines[0] == first)
        if last:
            assert(lines[-1] == last)

    # adding boundary tests
    def test_to_middle(self):
        self._test_from_to_line(None,
                            "Fri Oct 10 17:22:11.841",
                            "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                            "Fri Oct 10 17:22:11.839 [signalProcessingThread] shutdown: final commit...")

    def test_to_greater_than_file(self):
        self._test_from_to_line(None,
                                "2014-10-10 17:50:00.000000-00:00",
                                "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                "Fri Oct 10 17:48:55.648 dbexit: really exiting now")

    def test_to_second_last_line(self):
        self._test_from_to_line(None,
                                 "2014-10-10 17:48:54.000000-00:00",
                                 "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                 "Fri Oct 10 17:48:53.648 [signalProcessingThread] shutdown: removing fs lock...")

    def test_to_third_last_line(self):
        self._test_from_to_line(None,
                                "2014-10-10 17:48:53.000000-00:00",
                                "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                "Fri Oct 10 17:48:52.647 [signalProcessingThread] removeJournalFiles")

    def test_from_before_start_line(self):
        self._test_from_to_line("2014-10-10 17:00:00.000000-00:00",
                                None,
                                "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                "Fri Oct 10 17:48:55.648 dbexit: really exiting now",
                        )

    def test_from_start_line(self):
        self._test_from_to_line("2014-10-10 17:22:06.000000-00:00",
                                None,
                                "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                "Fri Oct 10 17:48:55.648 dbexit: really exiting now",
                        )

    def test_from_exact_start_line(self):
        self._test_from_to_line("2014-10-10 17:22:06.024000-00:00",
                                None,
                                "Fri Oct 10 17:22:06.024 [initandlisten] MongoDB starting : pid=93153 port=27017 dbpath=/data/db/ 64-bit host=Gianfranco-10gen.local",
                                "Fri Oct 10 17:48:55.648 dbexit: really exiting now",
                        )

    def test_from_after_start_line(self):
        self._test_from_to_line("2014-10-10 17:22:06.025000-00:00",
                                None,
                                "Fri Oct 10 17:22:07.025 [initandlisten]",
                                "Fri Oct 10 17:48:55.648 dbexit: really exiting now",
                        )

    def _test_from(self, date , first, last , path='test-mlogfilter-issue-50.log'):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', path)
        self.logfile = LogFile(open(self.logfile_path, 'r'))

        frm = parser.parse(date)
        self.tool.run('%s --from %s'%(self.logfile_path, frm.isoformat()))
        output = sys.stdout.getvalue()

        lines = output.splitlines()
        if first:
            assert(lines[0] == first)
        if last:
            assert(lines[-1] == last)


    def test_looper(self):
        random_start = parser.parse("2014-08-05 21:04:16+00:00")
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.isoformat()))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_to_wedged(self):
        """
        This results in the final while getting stuck on the line without a date time
        Mon Aug  5 20:55:20 [initandlisten] connection accepted from 10.0.0.12:52703 #143 (3 connections now open)
        === a line without a datetime ===
        Mon Aug  5 20:55:42 [initandlisten] connection accepted from 10.0.0.12:52710 #144 (4 connections now open)

        """

        random_start = parser.parse("2014-08-05 20:51:58+00:00")
        random_end  = parser.parse("2014-08-05 20:55:23+00:00")

        self.tool.run('%s --from %s --to %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start and le.datetime <= random_end)

    def test_from_to_single(self):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'single.log')
        self.logfile = LogFile(open(self.logfile_path, 'r'))

        random_start = parser.parse("2014-08-05 20:51:58+00:00")
        random_end  = parser.parse("2014-08-05 20:55:23+00:00")

        self.tool.run('%s --from %s --to %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start and le.datetime <= random_end)

    def test_msToString(self):
        assert(self.tool._msToString(100) == '0hr 0min 0secs 100ms')
        assert(self.tool._msToString(1000) == '0hr 0min 1secs 0ms')
        assert(self.tool._msToString(100000) == '0hr 1min 40secs 0ms')
        assert(self.tool._msToString(10000000) == '2hr 46min 40secs 0ms')

    def test_from(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        # random_start = parser.parse('2014-08-05 20:25:30+00:00')
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_iso8601_timestamp(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.isoformat()))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start)

    def test_from_to(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        random_end = random_date(random_start, self.logfile.end)

        self.tool.run('%s --from %s --to %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            assert(le.datetime >= random_start and le.datetime <= random_end)

    def test_from_to_26_log(self):
        logfile_26_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        logfile_26 = LogFile(open(logfile_26_path, 'r'))

        random_start = random_date(logfile_26.start, logfile_26.end)
        random_end = random_date(random_start+timedelta(minutes=1), logfile_26.end+timedelta(minutes=1))

        print random_start, random_end
        print logfile_26.start, logfile_26.end

        self.tool.run('%s --from %s --to %s'%(logfile_26_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0

        # round down
        start = random_start - timedelta(microseconds=random_start.microsecond)
        at_least_one = False
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            at_least_one = True
            assert(le.datetime >= start and le.datetime <= random_end)
        assert at_least_one

    def test_from_to_26_fail_log(self):
        """
        This test used to always fail so explicitly added
        """
        logfile_26_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        logfile_26 = LogFile(open(logfile_26_path, 'r'))

        # rounding error !
        random_start = parser.parse("2014-04-09 23:16:41.437000-04:00")
        random_end =  parser.parse("2014-04-09 23:29:03.437000-04:00")


        print random_start, random_end
        print logfile_26.start, logfile_26.end

        self.tool.run('%s --from %s --to %s'%(logfile_26_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0

        start = random_start - timedelta(microseconds=random_start.microsecond)

        at_least_one = False
        for line in output.splitlines():
            le = LogEvent(line)
            if not le.datetime:
                continue
            at_least_one = True
            assert(le.datetime >= start and le.datetime <= random_end)
        assert at_least_one

    def test_from_to_stdin(self):

        year = datetime.now().year
        start = datetime(year, 8, 5, 20, 45)
        end = datetime(year, 8, 5, 21, 01)
        self.tool.is_stdin = True
        self.tool.run('%s --from %s --to %s'%(self.logfile_path, start.strftime("%b %d %H:%M:%S"), end.strftime("%b %d %H:%M:%S")))
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.datetime >= start and le.datetime <= end)


    def test_json(self):
        """ output with --json is in JSON format. """
        self.tool.run('%s --json'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            line_dict = json.loads(line)
            assert(line_dict)
            assert(type(line_dict) == dict)

    def test_shorten_50(self):
        self.tool.run('%s --shorten 50'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 50)

    def test_shorten_default(self):
        self.tool.run('%s --shorten'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 200)

    def test_merge_same(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s'%(self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 2*file_length
        for prev, next in zip(lines[:-1], lines[1:]):
            prev_le = LogEvent(prev)
            next_le = LogEvent(next)
            if not prev_le.datetime or not next_le.datetime:
                continue
            assert prev_le.datetime <= next_le.datetime

    def test_merge_markers(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s --markers foo bar'%(self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len([l for l in lines if l.startswith('foo')]) == file_length
        assert len([l for l in lines if l.startswith('bar')]) == file_length

    def test_merge_invalid_markers(self):
        try:
            self.tool.run('%s %s --markers foo bar baz'%(self.logfile_path, self.logfile_path))
        except SystemExit as e:
            assert 'Number of markers not the same' in e.message

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
        self.tool.run('%s --from Jan 3015 --to +10min'%self.logfile_path)
        output = sys.stdout.getvalue()
        assert output.strip() == ''


    def test_human(self):
        # need to skip this test for python 2.6.x because thousands separator format is not compatible
        if sys.version_info < (2, 7):
            raise SkipTest

        self.tool.run('%s --slow --thread conn8 --human'%self.logfile_path)
        output = sys.stdout.getvalue().rstrip()
        assert(output.endswith('(0hr 0min 1secs 324ms) 1,324ms'))
        assert('cursorid:7,776,022,515,301,717,602' in output)

    def test_slow_fast(self):
        self.tool.run('%s --slow 145 --fast 500'%self.logfile_path)
        output = sys.stdout.getvalue()
        assert(len(output.splitlines()) > 0)
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.duration >= 145 and le.duration <= 500)

    def test_scan(self):
        # load tablescan logfile
        scn_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'collscans.log')

        self.tool.run('%s --scan' % scn_logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 3

    def test_accept_nodate(self):
        self.tool.is_stdin = True
        self.tool.run('%s --from Aug 5 2014 20:53:50 --to +5min'%self.logfile_path)
        self.tool.is_stdin = False

        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('=== a line without a datetime ===' in l for l in lines)

    def _test_thread(self,path,thread):
        self.tool.run('%s --thread mongosMain'%path )
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.thread == thread)
            md = re.match("^.* connection accepted from [0-9\.:]+ #(?P<conn>[0-9]+) " , le.line_str)
            if md is None:
                assert(le.conn is None)
            else:
                assert(le.conn == "conn" + md.group('conn'))

    def _test_thread_conn1(self,path,thread):
        self.tool.run('%s --thread conn1'%path )
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            md = re.match("^.* connection accepted from [0-9\.:]+ #(?P<conn>[0-9]+) " , le.line_str)
            assert(le.conn == 'conn1')
            if md is None:
                assert(le.thread == 'conn1')
            else:
                assert(le.thread == thread)

    def test_thread(self):
        self._test_thread(self.logfile_path,'initandlisten')

    def test_thread_conn1(self):
        self._test_thread_conn1(self.logfile_path,'initandlisten')

    def test_thread_mongos(self):
        mongos_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')
        self._test_thread(mongos_path,'mongosMain')

    def test_thread_mongos_conn1(self):
        mongos_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')
        self._test_thread_conn1(mongos_path,'mongosMain')

    def test_no_timestamp_format(self):
        self.tool.run('%s --timestamp-format none --timezone 5'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            if le.datetime:
                assert le.datetime_format == 'ctime-pre2.4'

    def test_operation(self):
        self.tool.run('%s --operation insert'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.operation == 'insert')

    def test_invalid_timezone_args(self):
        try:
            self.tool.run('%s --timezone 1 2 3'%self.logfile_path)
        except SystemExit as e:
            assert "Invalid number of timezone parameters" in e.message

    def test_verbose(self):
        self.tool.run('%s --slow --verbose'%self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert lines[0].startswith('command line arguments')
        assert any( line.startswith('active filters: SlowFilter') for line in lines )

    def test_namespace(self):
        self.tool.run('%s --namespace local.oplog.rs'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.namespace == 'local.oplog.rs')

    def test_pattern(self):
        # test that pattern is correctly parsed, reordered and compared to logevent pattern
        self.tool.run('%s --pattern {ns:1,_id:1,host:1}'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le = LogEvent(line)
            assert(le.pattern == '{"_id": 1, "host": 1, "ns": 1}')

    def test_word(self):
        self.tool.run('%s --word lock'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert('lock' in line)


    def test_mask_end(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - padding and le.datetime <= event1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )


    def test_mask_start(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        # mask_size = 45 # randrange(10, 60)
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center start'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - duration1 - padding and le.datetime <= event1 - duration1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )


    def test_mask_both(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15 UTC")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09 UTC")
        mask_size = randrange(10, 60)
        padding = timedelta(seconds=mask_size/2)

        self.tool.run('%s --mask %s --mask-size %i --mask-center both'%(self.logfile_path, mask_path, mask_size))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(
                    (le.datetime >= event1 - duration1 - padding and le.datetime <= event1 + padding) or
                    (le.datetime >= event2 - padding and le.datetime <= event2 + padding)
                  )

    @raises(SystemExit)
    def test_no_logfile(self):
        """ mlogfilter: test that not providing at least 1 log file throws clean error. """

        self.tool.run('--from Jan 1')


    def test_year_rollover_1(self):
        """ mlogfilter: test that mlogfilter works correctly with year-rollovers in logfiles with ctime (1) """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Jan 1 2014 --timestamp-format iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert line.startswith("2014-")


    def test_year_rollover_2(self):
        """ mlogfilter: test that mlogfilter works correctly with year-rollovers in logfiles with ctime (2) """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Dec 31 --to +1day --timestamp-format iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0
        for line in output.splitlines():
            assert line.startswith("2013-")


# output = sys.stdout.getvalue().strip()
