import sys, os
import mtools

from nose.tools import *
from mtools.util.logfile import LogFile
from mtools.util.logline import LogLine

class TestUtilLogFile(object):

    def setup(self):
        """ start up method to create mlaunch tool and find free port. """

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')
        self.filehandle = open(self.logfile_path, 'r')


    def test_len(self):
        """ LogFile: test len() and iteration over LogFile method """

        logfile = LogFile(self.filehandle)
        length = len(logfile)

        i = 0
        for i, ll in enumerate(logfile):
            assert isinstance(ll, LogLine)

        assert i+1 == length
