import io
import sys
from datetime import datetime

from dateutil.tz import tzutc
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import pytest

from mtools.mplotqueries.mplotqueries import MPlotQueriesTool


@pytest.fixture(autouse=True)
def _stdin_is_a_tty(monkeypatch):
    """Constructor must not try to read pytest's captured stdin."""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


def _install_plot_date():
    """Provide Axes.plot_date where this matplotlib no longer has it.

    Scatter plots on develop call plot_date. Matplotlib 3.9 removed it.
    The substitute draws the same markers so the legend can be checked.
    """
    if hasattr(plt.Axes, 'plot_date'):
        return

    def plot_date(self, x, y, *args, **kwargs):
        kwargs.setdefault('linestyle', 'None')
        kwargs.setdefault('marker', 'o')
        return self.plot(x, y, *args, **kwargs)

    plt.Axes.plot_date = plot_date


def _legend_labels(tool):
    if tool.legend is None:
        return []
    return [text.get_text() for text in tool.legend.get_texts()]


def _plot(path):
    _install_plot_date()
    tool = MPlotQueriesTool()
    out = path.parent / 'legend.png'
    tool.run('%s --output-file %s' % (path, out))
    return tool


LOG = (
    '2019-06-09T02:00:00.000+0000 I COMMAND  [conn1] command test.early '
    'command: find { find: "early", filter: { a: 1 } } '
    'planSummary: IXSCAN keysExamined:1 nreturned:1 5ms\n'
    '2019-06-09T04:00:00.000+0000 I COMMAND  [conn1] command test.late '
    'command: find { find: "late", filter: { a: 1 } } '
    'planSummary: IXSCAN keysExamined:1 nreturned:1 50ms\n'
)


def _when(hour, minute=0):
    return datetime(2019, 6, 9, hour, minute, tzinfo=tzutc())


def test_zooming_drops_groups_outside_the_view(tmp_path):
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    axis = plt.gca()

    assert set(_legend_labels(tool)) == {'test.early', 'test.late'}

    axis.set_xlim(date2num([_when(3, 30), _when(5)]))
    assert _legend_labels(tool) == ['test.late']
    picked = tool.legend.get_lines()[0]._mt_legend_item
    assert tool.artists[picked]._mt_group == 'test.late'

    axis.set_xlim(date2num([_when(3), _when(3, 30)]))
    assert _legend_labels(tool) == []

    axis.set_xlim(date2num([_when(1), _when(5)]))
    assert set(_legend_labels(tool)) == {'test.early', 'test.late'}

    axis.set_ylim(20, 100)
    assert _legend_labels(tool) == ['test.late']


def test_hidden_group_leaves_the_legend(tmp_path):
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    for artist in tool.artists:
        if getattr(artist, '_mt_group', None) == 'test.early':
            artist.set_visible(False)
    tool._refresh_legend(plt.gca())
    assert _legend_labels(tool) == ['test.late']
