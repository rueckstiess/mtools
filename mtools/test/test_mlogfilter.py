from mtools.mlogfilter.mlogfilter import MLogFilterTool
from nose.tools import *
from mtools.util.logline import LogLine
from random import randrange
from datetime import timedelta
import dateutil.parser
import os
import sys
import re


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
        self.log225_path = os.path.join('./logfiles/','mongod_225.log')

    def test_msToString(self):
        assert(self.tool._msToString(100) == '0hr 0min 0secs 100ms')
        assert(self.tool._msToString(1000) == '0hr 0min 1secs 0ms')
        assert(self.tool._msToString(100000) == '0hr 1min 40secs 0ms')
        assert(self.tool._msToString(10000000) == '2hr 46min 40secs 0ms')

    def test_from(self):
        self.tool.run('./logfiles/mongod_225.log --from Aug 5 21:04:52')
        output = sys.stdout.getvalue()
        assert(output.count('\n') == 25)

    def test_from_to(self):
        self.tool.run('./logfiles/mongod_225.log --from Aug 5 21:00:00 --to Aug 5 21:01:00')
        output = sys.stdout.getvalue()
        assert(output.count('\n') == 8)

    def test_shorten(self):
        self.tool.run('./logfiles/mongod_225.log --shorten 50')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert(len(line) <= 50)

    def test_human(self):
        self.tool.run('./logfiles/mongod_225.log --slow --thread conn8 --human')
        output = sys.stdout.getvalue().rstrip()
        assert(output.endswith('(0hr 0min 1secs 324ms) 1,324ms'))
        assert('cursorid:7,776,022,515,301,717,602' in output)

    def test_slow_fast(self):
        self.tool.run('./logfiles/mongod_225.log --slow 145 --fast 500')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            ll = LogLine(line)
            assert(ll.duration >= 145 and ll.duration <= 500)

    def test_thread(self):
        self.tool.run('./logfiles/mongod_225.log --thread initandlisten')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            ll = LogLine(line)
            assert(ll.thread == 'initandlisten')

    def test_operation(self):
        self.tool.run('./logfiles/mongod_225.log --operation insert')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            ll = LogLine(line)
            assert(ll.operation == 'insert')

    def test_namespace(self):
        self.tool.run('./logfiles/mongod_225.log --namespace local.oplog.rs')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            ll = LogLine(line)
            assert(ll.namespace == 'local.oplog.rs')

    def test_word(self):
        self.tool.run('./logfiles/mongod_225.log --word lock')
        output = sys.stdout.getvalue()
        for line in output.splitlines():
            assert('lock' in line)


# output = sys.stdout.getvalue().strip()