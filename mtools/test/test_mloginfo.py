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
import re


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
        results = self._parse_output(output)

        assert results['source'].endswith('mongod_225.log')
        assert results['host'] == 'capslock.local:27017'
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


    def test_version_norestart(self):
        # different log file
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'year_rollover.log')
        self.tool.run('%s' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'version: >= 2.4' in line, lines))


    def test_distinct_output(self):
        # different log file
        self.tool.run('%s --distinct' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'DISTINCT' in line, lines))
        assert len(filter(lambda line: re.match(r'\s+\d+\s+\w+', line), lines)) > 10


    def test_connections_output(self):
        # different log file
        self.tool.run('%s --connections' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'CONNECTIONS' in line, lines))

        assert any(map(lambda line: 'total opened' in line, lines))
        assert any(map(lambda line: 'total closed' in line, lines))
        assert any(map(lambda line: 'unique IPs' in line, lines))
        assert any(map(lambda line: 'socket exceptions' in line, lines))

        assert len(filter(lambda line: re.match(r'\d+\.\d+\.\d+\.\d+', line), lines)) > 1


    def test_queries_output(self):
        # different log file
        self.tool.run('%s --queries' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert any(map(lambda line: line.startswith('namespace'), lines))

        assert len(filter(lambda line: re.match(r'\w+\.\w+\s+{', line), lines)) >= 1


    def test_restarts_output(self):
        # different log file
        self.tool.run('%s --restarts' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'RESTARTS' in line, lines))
        assert any(map(lambda line: 'version 2.2.5' in line, lines))


    def test_corrupt(self):
        # load different logfile
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26_corrupt.log')
        self.tool.run('%s --queries' % logfile_path)

        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert any(map(lambda line: line.startswith('namespace'), lines))

        assert len(filter(lambda line: re.match(r'\w+\.\w+\.\w+\s+{', line), lines)) >= 1


    def test_rsstate_225(self):
        pattern = r'^Aug 05'
        expected = 13
        self._test_rsstate(self.logfile_path, pattern, expected)

    
    def test_rsstate_26(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        pattern = r'^Apr 09'
        expected = 17
        self._test_rsstate(logfile_path, pattern, expected)

    
    def test_rsstate_mongos(self):
        # different log file
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')
        pattern = r'  no rs state changes found'
        expected = 1
        self._test_rsstate(logfile_path, pattern, expected)

    
    def _test_rsstate(self, logfile_path, pattern, expected):
        """ utility test runner for rsstate
        """
        self.tool.run('%s --rsstate' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(filter(lambda line: re.match(pattern, line), lines)) == expected

    def test_rsinfo(self):
        self._test_rsinfo(self.logfile_path, **{'rs name':'replset',
                                                'rs version':'unknown',
                                                'rs members':'[ { host: "capslock.local:27017", _id: 0 }, { host: "capslock.local:27018", _id: 1 }, { host: "capslock.local:27019", _id: 2, arbiterOnly: true } ]'})

    
    def test_rsstate_26(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod_26.log')
        self._test_rsinfo(logfile_path,
                          **{'rs name':'shard01',
                             'rs version':'1',
                             'rs members':'[ { _id: 0, host: "enter.local:27019" }, { _id: 1, host: "enter.local:27020" }, { _id: 2, host: "enter.local:27021" } ]'})

    
    def test_rsstate_24(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongod-2411.log')
        self._test_rsinfo(logfile_path,
                          **{'rs name':'repl1',
                             'rs version':'unknown',
                             'rs members':'[ { host: "hostname.local:37018", _id: 0, votes: 1 }, { host: "hostname.local:37019", _id: 1, votes: 1 }, { host: "hostname.local:37020", _id: 2, arbiterOnly: true } ]'})

    
    def test_rsstate_mongos(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')
        self._test_rsinfo(logfile_path,**{'rs name':None, 'rs version':None,'rs members':None})

    
    def _test_rsinfo(self, logfile_path, **expected):
        """ utility test runner for rsstate
        """
        self.tool.run('%s --rsinfo' % logfile_path)
        output = sys.stdout.getvalue()
        results = self._parse_output(output)
        for key, value in expected.iteritems():
            print "results[",key,"] == " , value
            assert results.get(key) == value
        
    def _parse_output(self, output):
        results = {}
        for line in output.splitlines():
            if line.strip() == '' or ":" not in line:
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()
        return results

