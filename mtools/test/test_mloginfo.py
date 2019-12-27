import os
import re
import sys
from datetime import timedelta, date
from random import randrange

import six

import mtools
from mtools.mloginfo.mloginfo import MLogInfoTool
from mtools.util.logfile import LogFile


def random_date(start, end):
    """
    This function will return a random datetime between two datetime objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


class TestMLogInfo(object):
    """This class tests functionality around the mloginfo tool."""

    def setup(self):
        """Startup method to create mloginfo tool."""
        self.tool = MLogInfoTool()
        self._test_init()

    def _test_init(self, filename='mongod_225.log'):
        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                         'test/logfiles/', filename)
        self.logfile = LogFile(open(self.logfile_path, 'rb'))

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

    def test_28(self):
        self._test_init('mongod_278.log')
        self.tool.run('%s' % self.logfile_path)
        output = sys.stdout.getvalue()
        results = {}
        for line in output.splitlines():
            if line.strip() == '':
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()

        assert results['source'].endswith('mongod_278.log')
        assert results['host'] == 'capslock.local:27017'
        assert results['start'].endswith('2014 Oct 31 13:00:03.914')
        assert results['end'].endswith('2014 Oct 31 13:00:04.461')
        assert results['date format'] == 'iso8601-local'
        assert results['length'] == '25'
        assert results['binary'] == 'mongod'
        assert results['version'] == '2.7.8'
        assert results['storage'] == 'mmapv1'

    def test_28_no_restart(self):
        self._test_init('mongod_278_partial.log')
        self.tool.run('%s' % self.logfile_path)
        lines = sys.stdout.getvalue().splitlines()
        assert any(map(lambda line: '>= 3.0 (iso8601 format, level, component)'
                       in line, lines))

    def test_multiple_files(self):
        self.tool.run('%s %s' % (self.logfile_path, self.logfile_path))
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len([l for l in lines if l.strip().startswith('source')]) == 2
        assert len([l for l in lines if l.strip().startswith('start')]) == 2
        assert len([l for l in lines if l.strip().startswith('end')]) == 2
        assert len([l for l in lines if l.strip().startswith('-----')]) == 1

    def test_30_ctime(self):
        self._test_init('mongod_306_ctime.log')
        self.tool.run('%s' % self.logfile_path)
        output = sys.stdout.getvalue()
        results = {}
        for line in output.splitlines():
            if line.strip() == '':
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()

        assert results['source'].endswith('mongod_306_ctime.log')
        this_year = date.today().year
        expected = '{this_year} Jul 13 16:14:35.324'.format(**locals())
        assert results['start'].endswith(expected)
        assert results['end'].endswith(expected)
        assert results['date format'] == 'ctime'

    def test_30_ctime_queries(self):
        self._test_init('mongod_306_ctime.log')
        self.tool.run('%s --queries' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert not (any(map(lambda line: line.startswith('no queries found'),
                            lines)))
        assert any(map(lambda line: line.startswith('namespace'), lines))

    def test_version_norestart(self):
        # different log file
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'year_rollover.log')
        self.tool.run('%s' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: ('version: >= 2.4.x ctime '
                                     '(milliseconds present)') in line, lines))

    def test_distinct_output(self):
        # different log file
        self.tool.run('%s --distinct' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'DISTINCT' in line, lines))
        assert len(list(filter(lambda line: re.match(r'\s+\d+\s+\w+', line),
                          lines))) > 10

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

        assert len([re.match(r'\d+\.\d+\.\d+\.\d+', line) for line in lines]) > 1

    def test_connstats_output(self):
        # different log file
        self.tool.run('%s --connstats' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'CONNECTIONS' in line, lines))

        assert any(map(lambda line: 'total opened' in line, lines))
        assert any(map(lambda line: 'total closed' in line, lines))
        assert any(map(lambda line: 'unique IPs' in line, lines))
        assert any(map(lambda line: 'socket exceptions' in line, lines))
        assert any(map(lambda line: 'overall average connection duration(s):'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s):'
                       in line, lines))
        assert any(map(lambda line: 'overall maximum connection duration(s):'
                       in line, lines))

        assert len([re.match(r'\d+\.\d+\.\d+\.\d+', line) for line in lines]) > 1

    def test_connections_connstats_output(self):
        # different log file
        self.tool.run('%s --connections --connstats' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'CONNECTIONS' in line, lines))

        assert any(map(lambda line: 'total opened' in line, lines))
        assert any(map(lambda line: 'total closed' in line, lines))
        assert any(map(lambda line: 'unique IPs' in line, lines))
        assert any(map(lambda line: 'socket exceptions' in line, lines))
        assert any(map(lambda line: 'overall average connection duration(s):'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s):'
                       in line, lines))
        assert any(map(lambda line: 'overall maximum connection duration(s):'
                       in line, lines))

    def test_connstats_connid_repeated(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_start_'
                                     'connid_repeated.log'))
        try:
            self.tool.run('%s --connstats' % logfile_path)
        except NotImplementedError as e:
            assert("Multiple start datetimes found for the same connection ID"
                   in str(e))

    def test_connstats_endconnid_repeated(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_end_'
                                     'connid_repeated.log'))
        try:
            self.tool.run('%s --connstats' % logfile_path)
        except NotImplementedError as e:
            assert("Multiple end datetimes found for the same connection ID"
                   in str(e))

    def test_connstats_start_endconnid_repeated(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_start_'
                                     'end_connid_repeated.log'))
        try:
            self.tool.run('%s --connstats' % logfile_path)
        except NotImplementedError as e:
            assert("Multiple start datetimes found for the same connection ID"
                   in str(e))

    def test_connstats_connid_not_digit(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_start_'
                                     'connid_notdigit.log'))

        self.tool.run('%s --connstats' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line:
                       'overall average connection duration(s): 17'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s): 1'
                       in line, lines))
        assert any(map(lambda line:
                       'overall maximum connection duration(s): 33'
                       in line, lines))

    def test_connstats_end_connid_not_digit(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_end_'
                                     'connid_notdigit.log'))

        self.tool.run('%s --connstats' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: 'overall average connection duration(s): 1'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s): 1'
                       in line, lines))
        assert any(map(lambda line: 'overall maximum connection duration(s): 1'
                       in line, lines))

    def test_connstats_only_connection_end(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_'
                                     'only_connection_end.log'))

        self.tool.run('%s --connstats' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: 'overall average connection duration(s): -'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s): -'
                       in line, lines))
        assert any(map(lambda line: 'overall maximum connection duration(s): -'
                       in line, lines))

    def test_connstats_only_connection_accepted(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/connstats',
                                    ('mongod_3_4-9_connection_stats_'
                                     'only_connection_accepted.log'))

        self.tool.run('%s --connstats' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: 'overall average connection duration(s): -'
                       in line, lines))
        assert any(map(lambda line: 'overall minimum connection duration(s): -'
                       in line, lines))
        assert any(map(lambda line: 'overall maximum connection duration(s): -'
                       in line, lines))

    def test_queries_output(self):
        # different log file
        self.tool.run('%s --queries' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert any(map(lambda line: line.startswith('namespace'), lines))
        restring = r'\w+\.\w+\s+(query|update|getmore|allowDiskUse)\s+{'
        assert len(list(filter(lambda line: re.match(restring, line), lines))) >= 1

    def test_storagestats_output(self):
        # different log file
        self.logfile_path = "mtools/test/logfiles/mongod_4.0.10_storagestats.log"
        self.tool.run('%s --storagestats' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: '' in line, lines))
        assert any(map(lambda line: line.startswith('STORAGE STATISTICS '), lines))

    def test_transactions_output(self):
        # different log file
        logfile_transactions_path = 'mtools/test/logfiles/mongod_4.0.10_slowtransactions.log'
        self.tool.run('%s --transactions' % logfile_transactions_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'TRANSACTIONS' in line, lines))
        assert any(map(lambda line: line.startswith('DATETIME'), lines))

    def test_cursors_output(self):
        # different log file
        logfile_path = "mtools/test/logfiles/mongod_4.0.10_reapedcursor.log"
        self.tool.run('%s --cursors' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any('CURSOR' in line for line in lines)

    def test_restarts_output(self):
        # different log file
        self.tool.run('%s --restarts' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'RESTARTS' in line, lines))
        assert any(map(lambda line: 'version 2.2.5' in line, lines))

    def test_corrupt(self):
        # load different logfile
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26_corrupt.log')
        self.tool.run('%s --queries' % logfile_path)

        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert any(map(lambda line: 'QUERIES' in line, lines))
        assert any(map(lambda line: line.startswith('namespace'), lines))

        assert len(list(filter(lambda line: re.match(r'\w+\.\w+\.\w+\s+query\s+{',
                                                line), lines))) >= 1

    def test_rsstate_225(self):
        pattern = r'^Aug 05'
        expected = 13
        self._test_rsstate(self.logfile_path, pattern, expected)

    def test_rsstate_26(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26.log')
        pattern = r'^Apr 09'
        expected = 17
        self._test_rsstate(logfile_path, pattern, expected)

    def test_rsstate_mongos(self):
        # different log file
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongos.log')
        pattern = r'  no rs state changes found'
        expected = 1
        self._test_rsstate(logfile_path, pattern, expected)

    def _test_rsstate(self, logfile_path, pattern, expected):
        """ utility test runner for rsstate
        """
        self.tool.run('%s --rsstate' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()
        assert len(list(filter(lambda line: re.match(pattern, line),
                          lines))) == expected

    def test_rsinfo(self):
        rsmembers = ('[ { host: "capslock.local:27017", _id: 0 }, '
                     '{ host: "capslock.local:27018", _id: 1 }, '
                     '{ host: "capslock.local:27019", _id: 2, '
                     'arbiterOnly: true } ]')
        self._test_rsinfo(self.logfile_path, **{'rs name': 'replset',
                                                'rs version': 'unknown',
                                                'rs members': rsmembers})

    def test_rsstate_mongos_2(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongos.log')
        self._test_rsinfo(logfile_path, **{'rs name': None, 'rs version': None,
                                           'rs members': None})

    def _test_rsinfo(self, logfile_path, **expected):
        """ utility test runner for rsstate
        """
        self.tool.run('--rsinfo %s' % logfile_path)
        output = sys.stdout.getvalue()
        results = self._parse_output(output)
        for key, value in six.iteritems(expected):
            print("results[%s] == %s" % (key, value))
            assert results.get(key) == value

    def _parse_output(self, output):
        results = {}
        for line in output.splitlines():
            if line.strip() == '' or ":" not in line:
                continue
            key, val = line.split(':', 1)
            results[key.strip()] = val.strip()
        return results

    def test_avoid_dict_sorting(self):
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'issue-636.log')
        self.tool.run('%s --queries' % logfile_path)
