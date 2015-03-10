import sys, os
import mtools

from nose.tools import *
from datetime import datetime
from mtools.util.logfile import LogFile
from mtools.util.logevent import LogEvent
from dateutil.tz import tzutc, tzoffset


class TestUtilLogFile(object):

    def setup(self):
        """ start up method for LogFile fixture. """

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')
        self.file_year_rollover = open(self.logfile_path, 'r')


    def test_len(self):
        """ LogFile: test len() and iteration over LogFile method """

        logfile = LogFile(self.file_year_rollover)
        length = len(logfile)

        i = 0
        for i, le in enumerate(logfile):
            assert isinstance(le, LogEvent)

        assert length == i+1 
        assert length == 1836


    def test_start_end(self):
        """ LogFile: test .start and .end property work correctly """

        logfile = LogFile(self.file_year_rollover)
        
        assert logfile.start == datetime(2014, 12, 30, 00, 13, 01, 661000, tzutc())
        assert logfile.end == datetime(2015, 01, 02, 23, 27, 11, 720000, tzutc())


    def test_timezone(self):

        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        mongod_26 = open(logfile_path, 'r')

        logfile = LogFile(mongod_26)
        assert logfile.timezone == tzoffset(None, -14400)


    def test_rollover_detection(self):
        """ LogFile: test datetime_format and year_rollover properties """

        logfile = LogFile(self.file_year_rollover)
        assert logfile.datetime_format == "ctime"
        assert logfile.year_rollover == logfile.end


    def test_storage_engine_detection(self):
        """ LogFile: test if the correct storage engine is detected """

        logfile = LogFile(self.file_year_rollover)
        assert logfile.storage_engine == None

        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        mmapv1 = open(logfile_path, 'r')
        logfile = LogFile(mmapv1)
        assert logfile.storage_engine == 'mmapv1'

        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'wiredtiger.log')
        wiredtiger = open(logfile_path, 'r')
        logfile = LogFile(wiredtiger)
        assert logfile.storage_engine == 'wiredTiger'
        

    def test_hostname_port(self):
        # mongod
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        mongod_26 = open(logfile_path, 'r')

        logfile = LogFile(mongod_26)
        assert logfile.hostname == 'enter.local'
        assert logfile.port == '27019'

        # mongos
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')
        mongos = open(logfile_path, 'r')

        logfile2 = LogFile(mongos)
        print logfile2.hostname
        assert logfile2.hostname == 'jimoleary.local'
        assert logfile2.port == '27017'
