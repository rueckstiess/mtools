from mtools.mloginfo.mloginfo import MLogInfoTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile
import mtools

from nose.tools import *
from nose.plugins.skip import Skip, SkipTest

# from random import randrange
# from datetime import timedelta, datetime
# from dateutil import parser
import os
import sys
# import re
# import json


def random_date(start, end):
    """ This function will return a random datetime between two datetime objects. """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogInfo(object):
    """ This class tests functionality around the mloginfo tool. """

    def setup(self):
        """ startup method to create mloginfo tool. """
        self.tool = MLogInfoTool()

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_225.log')
        self.logfile = LogFile(open(self.logfile_path, 'r'))


    def test_basic(self):
        self.tool.run('%s' % self.logfile_path)
        output = sys.stdout.getvalue()
        results = {}
        for line in output.splitlines():
            if line.strip() == '':
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()

        assert results['source'].endswith('mongod_225.log')
        assert results['start'].endswith('Aug 05 20:21:42')
        assert results['end'].endswith('Aug 05 21:04:52')
        assert results['date format'] == 'ctime-pre2.4'
        assert results['length'] == '497'
        assert results['binary'] == 'mongod'
        assert results['version'] == '2.2.5'


    def test_multiple_files(self):
        self.tool.run('%s %s' % (self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        results = {}
        lines = output.splitlines()
        assert len( [l for l in lines if l.strip().startswith('source') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('start') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('end') ] ) == 2
        assert len( [l for l in lines if l.strip().startswith('-----') ] ) == 1




