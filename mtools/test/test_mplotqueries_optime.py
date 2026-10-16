import io
import sys
from datetime import datetime, timedelta

from dateutil.tz import tzutc
import pytest

from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.util.logfile import LogFile


@pytest.fixture(autouse=True)
def _stdin_is_a_tty(monkeypatch):
    """Constructor must not try to read pytest's captured stdin."""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


LOG = (
    '2019-06-09T02:18:02.194+0000 I COMMAND  [conn1] command test.foo '
    'command: find { find: "foo", filter: { a: 1 } } planSummary: IXSCAN '
    'keysExamined:1 docsExamined:1 nreturned:1 5000ms\n'
    '2019-06-09T02:18:07.194+0000 I COMMAND  [conn1] command test.bar '
    'command: find { find: "bar", filter: { a: 1 } } planSummary: IXSCAN '
    'keysExamined:1 docsExamined:1 nreturned:1 10ms\n'
)


def _view(path, *extra):
    tool = MPlotQueriesTool()
    tool.plot = lambda: None
    tool.run('%s %s' % (path, ' '.join(extra)))
    return tool.plot_instances[0].date_range


def test_optime_start_includes_the_operation_start(tmp_path):
    path = tmp_path / 'op.log'
    path.write_text(LOG)
    with open(path, 'rb') as handle:
        logfile = LogFile(handle)
        logged_start = logfile.start

    view_start, view_end = _view(str(path), '--optime-start')
    assert view_start == logged_start - timedelta(milliseconds=5000)
    assert view_start < logged_start
    assert view_end >= datetime(2019, 6, 9, 2, 18, 7, tzinfo=tzutc())


def test_default_view_stays_on_the_log_bounds(tmp_path):
    path = tmp_path / 'op.log'
    path.write_text(LOG)
    with open(path, 'rb') as handle:
        logfile = LogFile(handle)
        logged_start = logfile.start
        logged_end = logfile.end

    view_start, view_end = _view(str(path))
    assert view_start == logged_start
    assert view_end == logged_end


def test_durline_view_includes_the_operation_start(tmp_path):
    path = tmp_path / 'op.log'
    path.write_text(LOG)
    with open(path, 'rb') as handle:
        logfile = LogFile(handle)
        logged_start = logfile.start

    view_start, _ = _view(str(path), '--type', 'durline')
    assert view_start == logged_start - timedelta(milliseconds=5000)


def test_optime_start_view_covers_several_logfiles(tmp_path):
    first = tmp_path / 'one.log'
    second = tmp_path / 'two.log'
    first.write_text(LOG)
    second.write_text(LOG.replace('02:18:', '03:18:'))

    tool = MPlotQueriesTool()
    tool.plot = lambda: None
    tool.run('%s %s --optime-start' % (first, second))
    view_start, view_end = tool.plot_instances[0].date_range
    assert view_start == datetime(2019, 6, 9, 2, 17, 57, 194000,
                                  tzinfo=tzutc())
    assert view_end >= datetime(2019, 6, 9, 3, 18, 7, tzinfo=tzutc())
