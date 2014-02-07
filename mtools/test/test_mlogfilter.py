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


    def test_msToString(self):
        assert(self.tool._msToString(100) == '0hr 0min 0secs 100ms')
        assert(self.tool._msToString(1000) == '0hr 0min 1secs 0ms')
        assert(self.tool._msToString(100000) == '0hr 1min 40secs 0ms')
        assert(self.tool._msToString(10000000) == '2hr 46min 40secs 0ms')

    def test_from(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        self.tool.run('%s --from %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(le.datetime >= random_start)

    def test_from_to(self):
        random_start = random_date(self.logfile.start, self.logfile.end)
        random_end = random_date(random_start, self.logfile.end)

        self.tool.run('%s --from %s --to %s'%(self.logfile_path, random_start.strftime("%b %d %H:%M:%S"), random_end.strftime("%b %d %H:%M:%S")))
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(le.datetime >= random_start and le.datetime <= random_end)

    def test_json(self):
        """ output with --json is in JSON format. """
        self.tool.run('%s --json'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            line_dict = json.loads(line)
            assert(line_dict)
            assert(type(line_dict) == dict)

    def test_shorten(self):
        self.tool.run('%s --shorten 50'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 50)

    def test_merge_same(self):
        file_length = len(self.logfile)
        self.tool.run('%s %s'%(self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(lines) == 2*file_length
        for prev, next in zip(lines[:-1], lines[1:]):
            assert LogEvent(prev).datetime <= LogEvent(next).datetime


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
            le =  LogEvent(line)
            assert(le.duration >= 145 and le.duration <= 500)

    def test_thread(self):
        self.tool.run('%s --thread initandlisten'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(le.thread == 'initandlisten')

    def test_operation(self):
        self.tool.run('%s --operation insert'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(le.operation == 'insert')

    def test_namespace(self):
        self.tool.run('%s --namespace local.oplog.rs'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert(le.namespace == 'local.oplog.rs')

    def test_word(self):
        self.tool.run('%s --word lock'%self.logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert('lock' in line)


    def test_mask_end(self):
        mask_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mask_centers.log')

        event1 = parser.parse("Mon Aug  5 20:27:15")
        event2 = parser.parse("Mon Aug  5 20:30:09")
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

        event1 = parser.parse("Mon Aug  5 20:27:15")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09")
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

        event1 = parser.parse("Mon Aug  5 20:27:15")
        duration1 = timedelta(seconds=75)
        event2 = parser.parse("Mon Aug  5 20:30:09")
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

        self.tool.run('%s --from Jan 1' % yro_logfile_path)
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            le =  LogEvent(line)
            assert le.datetime.year == 2014 


    def test_year_rollover_2(self):
        """ mlogfilter: test that mlogfilter works correctly with year-rollovers in logfiles with ctime (2) """

        # load year rollover logfile
        yro_logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')

        self.tool.run('%s --from Dec 31 --to +1day --timestamp-format iso8601-utc' % yro_logfile_path)
        output = sys.stdout.getvalue()
        assert len(output.splitlines()) > 0
        for line in output.splitlines():
            le = LogEvent(line)
            assert le.datetime.year == 2013


# output = sys.stdout.getvalue().strip()