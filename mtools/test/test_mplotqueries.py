import sys
import os

import mtools
from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.util.logfile import LogFile
from nose.plugins.skip import SkipTest
from nose.tools import raises

class TestMPlotQueries(object):

    def setup(self):
        """Startup method to create mplotqueries tool."""
        self.tool = MPlotQueriesTool()
        self._test_init()

    def _test_init(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))

    def test_checkpoints(self, filename='mongod_4.0.10_slowcheckpoints.log'):
        raise SkipTest('Skipping interactive test')
        # different logfile for the slow Checkpoints
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', filename)
        self.tool.run('%s --checkpoints' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'SCATTER plot' in line, lines))
