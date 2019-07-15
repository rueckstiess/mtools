import sys
import os
import mtools

from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.util.logfile import LogFile


class TestMPlotQueries(object):

    def setup(self):
        """Startup method to create mloginfo tool."""
        self.tool = MPlotQueriesTool()
        self._test_init()

    def _test_init(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))

    def test_oplog(self):
        # different logfile for oplogs
        logfile_oplog = "mtools/test/logfiles/mongod_4.0.10_slowoplogs.log"
        self.tool.run('%s --oplog --group operation' % logfile_oplog)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('SCATTER plot' in line for line in lines)