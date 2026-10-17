import io
import json
import os
import re
import sys
import tempfile

import pytest

import mtools
from mtools.mloginfo.mloginfo import MLogInfoTool
from mtools.util.logevent import LogEvent


@pytest.fixture(autouse=True)
def patch_stdin(monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


_ROW = re.compile(
    r'^(?P<namespace>\S+)\s+'
    r'(?P<operation>query|getmore|update|remove|find|aggregate|'
    r'count|findandmodify|geonear)\s+'
    r'(?P<pattern>\{.*\}|None)\s+'
    r'(?P<count>\d+)\b'
)


def _table_rows(output):
    """Return the data rows of an mloginfo --queries table."""
    rows = []
    for line in output.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        rows.append({'namespace': match.group('namespace'),
                     'operation': match.group('operation'),
                     'pattern': match.group('pattern'),
                     'count': int(match.group('count'))})
    return rows


def _queries(text, capsys):
    handle = tempfile.NamedTemporaryFile('w', suffix='.log', delete=False)
    try:
        handle.write(text)
        if not text.endswith('\n'):
            handle.write('\n')
        handle.close()
        tool = MLogInfoTool()
        tool.run('%s --queries' % handle.name)
        output = capsys.readouterr().out
    finally:
        os.unlink(handle.name)
    return _table_rows(output)


def _legacy(clock, body):
    return '2019-06-09T02:18:%s.000Z [conn1] %s' % (clock, body)


def _logv2(clock, attr):
    doc = {'t': {'$date': '2019-06-09T02:18:%s.000+00:00' % clock},
           's': 'I', 'c': 'COMMAND', 'id': 51803, 'ctx': 'conn1',
           'msg': 'Slow query', 'attr': attr}
    return json.dumps(doc)


def test_cursorid_from_getmore_line():
    line = ("Mon Aug  5 20:26:32 [conn9] getmore local.oplog.rs "
            "query: { ts: { $gte: new Date(5908578361554239489) } } "
            "cursorid:1870634279361287923 ntoreturn:0 keyUpdates:0 "
            "numYields: 107 locks(micros) r:85093 nreturned:13551 "
            "reslen:230387 144ms")
    event = LogEvent(line)
    assert event.cursorid == 1870634279361287923
    assert event.originating_pattern is None


def test_cursorid_with_commas_and_zero():
    counted = ("2019-06-09T02:18:02.000Z [conn1] getmore test.orders "
               "cursorid:7,776,022,515,301,717,602 nreturned:1 2ms")
    assert LogEvent(counted).cursorid == 7776022515301717602

    closed = ("2019-06-09T02:18:02.000Z [conn1] query test.orders "
              "query: { a: 1 } cursorid:0 nreturned:1 2ms")
    assert LogEvent(closed).cursorid is None


def test_originating_command_pattern():
    line = ("2019-06-09T02:18:07.000Z [conn2] command test.orders "
            "command: getMore { getMore: 555, collection: \"orders\" } "
            "originatingCommand: { find: \"orders\", filter: { sku: \"abc\" }, "
            "$db: \"test\" } cursorid:555 nreturned:3 30ms")
    event = LogEvent(line)
    assert event.cursorid == 555
    assert event.originating_pattern == '{"sku": 1}'


def test_getmores_follow_the_query_that_opened_the_cursor(capsys):
    text = '\n'.join([
        _legacy('02', 'query test.orders query: { status: "open" } '
                'cursorid:111 nreturned:1 5ms'),
        _legacy('03', 'getmore test.orders cursorid:111 nreturned:20 80ms'),
        _legacy('04', 'getmore test.orders cursorid:111 nreturned:20 70ms'),
        _legacy('05', 'query test.orders query: { sku: "abc", qty: 2 } '
                'cursorid:222 nreturned:1 6ms'),
        _legacy('06', 'getmore test.orders cursorid:222 nreturned:4 90ms'),
        _legacy('07', 'getmore test.orders cursorid:333 nreturned:1 40ms'),
    ])
    rows = _queries(text, capsys)
    getmores = [row for row in rows if row['operation'] == 'getmore']
    by_pattern = {row['pattern']: row for row in getmores}

    assert by_pattern['{"status": 1}']['count'] == 2
    assert by_pattern['{"qty": 1, "sku": 1}']['count'] == 1
    assert by_pattern['None']['namespace'] == 'test.orders'
    assert by_pattern['None']['count'] == 1
    assert len(getmores) == 3


def test_same_query_shape_stays_on_one_row(capsys):
    text = '\n'.join([
        _legacy('02', 'query test.orders query: { a: 1 } '
                'cursorid:10 nreturned:1 5ms'),
        _legacy('03', 'getmore test.orders cursorid:10 nreturned:2 20ms'),
        _legacy('04', 'query test.orders query: { a: 9 } '
                'cursorid:20 nreturned:1 5ms'),
        _legacy('05', 'getmore test.orders cursorid:20 nreturned:2 30ms'),
    ])
    rows = _queries(text, capsys)
    getmores = [row for row in rows if row['operation'] == 'getmore']
    assert len(getmores) == 1
    assert getmores[0]['pattern'] == '{"a": 1}'
    assert getmores[0]['count'] == 2


def test_cursor_id_zero_does_not_join_getmores(capsys):
    text = '\n'.join([
        _legacy('02', 'query test.orders query: { a: 1 } '
                'cursorid:0 nreturned:1 5ms'),
        _legacy('03', 'getmore test.orders cursorid:0 nreturned:2 20ms'),
        _legacy('04', 'query test.orders query: { b: 1, c: 1 } '
                'cursorid:0 nreturned:1 5ms'),
        _legacy('05', 'getmore test.orders cursorid:0 nreturned:2 30ms'),
    ])
    rows = _queries(text, capsys)
    getmores = [row for row in rows if row['operation'] == 'getmore']
    assert len(getmores) == 1
    assert getmores[0]['pattern'] == 'None'
    assert getmores[0]['count'] == 2


def test_originating_command_without_the_opening_query(capsys):
    text = _legacy(
        '07',
        'command test.orders command: getMore '
        '{ getMore: 555, collection: "orders" } '
        'originatingCommand: { find: "orders", filter: { sku: "abc" }, '
        '$db: "test" } cursorid:555 nreturned:3 30ms')
    rows = _queries(text, capsys)
    assert rows == [{'namespace': 'test.orders',
                     'operation': 'getmore',
                     'pattern': '{"sku": 1}',
                     'count': 1}]


def test_later_getmore_reuses_originating_command(capsys):
    text = '\n'.join([
        _legacy('07',
                'command test.orders command: getMore '
                '{ getMore: 555, collection: "orders" } '
                'originatingCommand: { find: "orders", filter: { sku: "abc" } } '
                'cursorid:555 nreturned:3 30ms'),
        _legacy('08', 'getmore test.orders cursorid:555 nreturned:3 40ms'),
    ])
    rows = _queries(text, capsys)
    getmores = [row for row in rows if row['operation'] == 'getmore']
    assert len(getmores) == 1
    assert getmores[0]['pattern'] == '{"sku": 1}'
    assert getmores[0]['count'] == 2


def test_logv2_getmore_uses_originating_command(capsys):
    find = _logv2('02', {
        'type': 'command',
        'ns': 'test.orders',
        'command': {'find': 'orders', 'filter': {'status': 'open'},
                    '$db': 'test'},
        'cursorid': 111,
        'nReturned': 1,
        'durationMillis': 5,
    })
    other = _logv2('03', {
        'type': 'command',
        'ns': 'test.orders',
        'command': {'find': 'orders', 'filter': {'sku': 'abc', 'qty': 2},
                    '$db': 'test'},
        'cursorid': 222,
        'nReturned': 1,
        'durationMillis': 6,
    })
    # The opening find for cursor 333 was not logged. The getMore still
    # carries the query that created it.
    followed = _logv2('04', {
        'type': 'command',
        'ns': 'test.orders',
        'command': {'getMore': 333, 'collection': 'orders', '$db': 'test'},
        'originatingCommand': {'find': 'orders',
                               'filter': {'userId': 5},
                               '$db': 'test'},
        'cursorid': 333,
        'nReturned': 8,
        'durationMillis': 40,
    })
    getmore = _logv2('05', {
        'type': 'command',
        'ns': 'test.orders',
        'command': {'getMore': 111, 'collection': 'orders', '$db': 'test'},
        'cursorid': 111,
        'nReturned': 20,
        'durationMillis': 80,
    })
    rows = _queries('\n'.join([find, other, followed, getmore]), capsys)
    getmores = {row['pattern']: row for row in rows
                if row['operation'] == 'getmore'}
    assert getmores['{"status": 1}']['count'] == 1
    assert getmores['{"userId": 1}']['count'] == 1
    assert '{"qty": 1, "sku": 1}' not in getmores


def test_logged_getmore_pattern_is_unchanged_without_an_opener(capsys):
    logfile = os.path.join(os.path.dirname(mtools.__file__),
                           'test/logfiles/', 'mongod_225.log')
    tool = MLogInfoTool()
    tool.run('%s --queries' % logfile)
    rows = _table_rows(capsys.readouterr().out)
    matched = [row for row in rows
               if row['operation'] == 'getmore' and
               row['namespace'] == 'local.oplog.rs']
    assert len(matched) == 1
    assert matched[0]['pattern'] == '{"ts": 1}'
    assert matched[0]['count'] == 7
