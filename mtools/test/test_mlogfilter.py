from mtools.mlogfilter.mlogfilter import MLogFilterTool
from nose.tools import *
import os
import sys

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
        assert(output.count('\n') == 25)

    def test_to(self):
        pass

    def test_slow_fast(self):
        pass

    def test_thread(self):
        pass

    def test_operation(self):
        pass





# output = sys.stdout.getvalue().strip()