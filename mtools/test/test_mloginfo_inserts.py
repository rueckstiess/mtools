import io
import sys

import pytest

from mtools.mloginfo.mloginfo import MLogInfoTool


@pytest.fixture(autouse=True)
def _stdin_is_a_tty(monkeypatch):
    """Constructor must not try to read pytest's captured stdin."""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


LOG = """\
Mon Aug  5 20:22:10 [conn4] insert test.docs keyUpdates:0 \
locks(micros) w:288340 288ms
2014-04-09T23:19:26.551-0400 [conn48] insert test.system.indexes \
query: { ns: "test.docs", key: { foo: "hashed" }, name: "foo_hashed" } \
ninserted:1 keyUpdates:0 numYields:0 locks(micros) w:182206 182ms
2019-06-18T12:05:36.423+0100 I COMMAND  [conn2] command local.orders \
command: insert { insert: "orders", documents: [ { sku: "abc", qty: 2 } ], \
ordered: true } ninserted:1 keysInserted:1 numYields:0 2ms
2019-06-18T12:05:37.423+0100 I COMMAND  [conn2] command local.orders \
command: find { find: "orders", filter: { sku: "abc" } } \
keysExamined:1 nreturned:1 5ms
"""


def test_queries_include_inserts(tmp_path, capsys):
    path = tmp_path / 'inserts.log'
    path.write_text(LOG)
    MLogInfoTool().run('%s --queries' % path)
    lines = capsys.readouterr().out.splitlines()
    text = '\n'.join(lines)

    assert 'no queries found.' not in text
    assert any(line.split()[:2] == ['test.docs', 'insert'] for line in lines)
    assert any(line.split()[:2] == ['test.system.indexes', 'insert']
               and '"foo": 1' in line for line in lines)
    assert any(line.split()[:2] == ['local.orders', 'insert']
               and '"sku": 1' in line for line in lines)
    assert any(line.split()[:2] == ['local.orders', 'find']
               and '"sku": 1' in line for line in lines)
