import sys
from datetime import datetime, timedelta
from random import randrange

from dateutil import parser
import pytest

import os

import mtools
from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile


@pytest.fixture(scope="function", autouse=True)
def patch_io(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('my input'))
    sys.stdin.name = 'foo'
    sys.stdin.isatty = lambda: True

    
class TestMPlotQueries(object):

    def setup_method(self):
        """Startup method to create mplotqueries tool."""
        self.tool = MPlotQueriesTool()
        self._test_init()

    def _test_init(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))

    @pytest.mark.skip(reason='Skipping interactive test')
    def test_dns(self, filename='mongod_4.0.10_slowdns.log'):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),'test/logfiles/', filename)
        self.tool.run('%s --dns' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'SCATTER plot' in line, lines))

    @pytest.mark.skip(reason='Skipping interactive test')
    def test_checkpoints(self, filename='mongod_4.0.10_slowcheckpoints.log'):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', filename)
        self.tool.run('%s --checkpoints' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'SCATTER plot' in line, lines))

    @pytest.mark.skip(reason='Skipping interactive test')
    def test_oplog(self, filename='mongod_4.0.10_slowoplogs.log'):
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', filename)
        self.tool.run('%s --oplog --group operation' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('SCATTER plot' in line for line in lines)
