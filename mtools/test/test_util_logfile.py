import sys, os
import mtools

from nose.tools import *
from datetime import datetime
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

        assert length == i+1 
        assert length == 1836


    def test_start_end(self):
        """ LogFile: test .start and .end property work correctly """

        logfile = LogFile(self.filehandle)
        
        assert logfile.start == datetime(2013, 12, 30, 00, 13, 01, 661000)
        assert logfile.end == datetime(2014, 01, 02, 23, 27, 11, 720000)
