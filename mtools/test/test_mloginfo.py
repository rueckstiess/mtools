import io
import os
import re
import sys
from datetime import timedelta, date
from random import randrange

import pytest

import mtools
from mtools.mloginfo.mloginfo import MLogInfoTool
from mtools.util.logfile import LogFile


@pytest.fixture(scope="function", autouse=True)
def patch_io(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('my input'))
    sys.stdin.name = 'foo'
    sys.stdin.isatty = lambda: True


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

    def setup_method(self):
        """Startup method to create mloginfo tool."""
        self.tool = MLogInfoTool()
        self._test_init()

    @classmethod
    def _test_init(cls, filename='mongod_225.log'):
        # load logfile(s)
        cls.logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                         'test/logfiles/', filename)
        cls.logfile = LogFile(open(cls.logfile_path, 'rb'))

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
        for key, value in expected.items():
            print("results[%s] == %s" % (key, value))
            assert results.get(key) == value

    def test_sharding_missing_information(self):
        self.tool.run('--sharding --errors --migrations %s' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: 'no sharding info found.' in line, lines))
        assert any(map(lambda line: 'no error messages found.' in line, lines))
        assert any(map(lambda line: 'no chunk migrations found.' in line, lines))
        assert any(map(lambda line: 'no chunk migrations found.' in line, lines))
        assert any(map(lambda line: 'no chunk splits found.' in line, lines))

    def test_sharding_overview_shard(self):
        self._test_init('sharding_360_shard.log')
        self.tool.run('--sharding %s' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: '(shard)' in line, lines))
        assert any(map(lambda line: 'shard01' in line, lines))
        assert any(map(lambda line: 'localhost:27018,'
                                    'localhost:27019,'
                                    'localhost:27020' in line, lines))
        assert any(map(lambda line: 'configRepl' in line, lines))
        assert any(map(lambda line: 'localhost:27033' in line, lines))

    def test_sharding_overview_csrs(self):
        self._test_init('sharding_360_CSRS.log')
        self.tool.run('--sharding %s' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: '(CSRS)' in line, lines))
        assert any(map(lambda line: 'shard01' in line, lines))
        assert any(map(lambda line: 'localhost:27018,'
                                    'localhost:27019,'
                                    'localhost:27020' in line, lines))
        assert any(map(lambda line: 'configRepl' in line, lines))
        assert any(map(lambda line: '[ { _id: 0, host: "localhost:27033",' 
                                    ' arbiterOnly: false, buildIndexes: true,'
                                    ' hidden: false, priority: 1.0, tags: {},'
                                    ' slaveDelay: 0, votes: 1 } ]' in line, lines))
        
    def test_sharding_overview_mongos(self):
        self._test_init('sharding_360_mongos.log')
        self.tool.run('--sharding %s' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        assert any(map(lambda line: '(mongos)' in line, lines))
        assert any(map(lambda line: 'shard01' in line, lines))
        assert any(map(lambda line: 'localhost:27018,'
                                    'localhost:27019,'
                                    'localhost:27020' in line, lines))
        assert any(map(lambda line: 'configRepl' in line, lines))
        assert any(map(lambda line: 'localhost:27033' in line, lines))

    def test_sharding_error_messages_exists(self):
        self._test_init('sharding_360_shard.log')
        self.tool.run('--sharding --errors %s' % self.logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        # Find errors which match the format "  <count> <error_message>"
        assert len(list(filter(lambda line: re.match('^  \d .* ', line),
                          lines))) == 1

    def test_sharding_chunk_migration_from_exists(self):
        self._test_init('sharding_360_shard.log')
        table_header = "TO SHARD"
        table_rows = []
        table_rows.append(
            ["2020-02-07T12",
             "shard03",
             "test.products",
             "1 chunk(s)",
             "1 chunk(s) moved | Total time spent: 16144ms",
             "no failed chunks."]
        )
        table_rows.append(
            ["2020-02-07T12",
             "shard02",
             "test.products",
             "1 chunk(s)",
             "1 chunk(s) moved | Total time spent: 13987ms",
             "no failed chunks."]
        )
        number_of_rows = 2
        self._test_sharding(self.logfile_path, table_header, table_rows, number_of_rows)

    def test_sharding_chunk_migration_to_exists(self):
        self._test_init('sharding_360_shard.log')
        table_header = "FROM SHARD"
        table_rows = []
        table_rows.append(
            ["2020-02-07T12",
             "Unknown",
             "test.products",
             "1 chunk(s)",
             "1 chunk(s) moved | Total time spent: 13676ms",
             "no failed chunks."]
        )
        number_of_rows = 1
        self._test_sharding(self.logfile_path, table_header, table_rows, number_of_rows)

    def test_sharding_chunk_split_statistics_exist(self):
        self._test_init('sharding_360_shard.log')
        table_header = "# SPLIT-VECTORS ISSUED"
        table_rows = []
        table_rows.append(
            ["2020-02-07T12",
             "test.products",
             "2 split vector(s)",
             "1 chunk(s) splitted | Total time spent: 14ms",
             "no failed chunk splits."]
        )
        number_of_rows = 1
        self._test_sharding(self.logfile_path, table_header, table_rows, number_of_rows)

    def test_sharding_jumbo_chunk_exists(self):
        self._test_init('sharding_360_CSRS.log')
        table_header = "# SPLIT-VECTORS ISSUED"
        table_rows = []
        table_rows.append(
            ["2020-02-07T15",
             "test.products",
             "0 split vector(s)",
             "0 chunk(s) splitted | Total time spent: 0ms",
             "1 chunk(s): ['15:47:18.485'] marked as Jumbo."]
        )
        number_of_rows = 1
        self._test_sharding(self.logfile_path, table_header, table_rows, number_of_rows)

    def _test_sharding(self, logfile_path, table_header, table_rows, number_of_rows):
        """ utility test runner for sharding tables
        """
        self.tool.run('--sharding --migrations %s' % logfile_path)
        output = sys.stdout.getvalue()
        lines = output.splitlines()

        for index, line in enumerate(lines):
            if re.search(f'{table_header}', line):
                # Skip the new lines between header and row
                table_index = index + 2
                break

        # Only grab lines which should be the rows for the wanted table
        searched_table = lines[table_index: table_index+number_of_rows]
        
        # Filter through to compare table rows
        for index, row in enumerate(searched_table):
            # Strip all tabs in line
            split_row = list(filter(None, re.sub(r'\s{2,}', '/', row).split("/")))
            assert (split_row == table_rows[index])

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
