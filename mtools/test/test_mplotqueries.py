import sys
from datetime import datetime, timedelta
from random import randrange

from dateutil import parser
from nose.plugins.skip import SkipTest
from nose.tools import raises

import os

import mtools
from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile


class TestMPlotQueries(object):

    def setup(self):
        """Startup method to create mplotqueries tool."""
        self.tool = MPlotQueriesTool()
        self._test_init()

    def _test_init(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))

    def test_storagestats(self, filename='mongod_4.0.10_storagestats.log'):
        #different logfile for DNS
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.tool.run('%s --storagestats --yaxis bytesRead' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'SCATTER plot' in line, lines))