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


def test_hidden_group_stays_in_the_legend(tmp_path):
    """A hidden series keeps its entry so it can be toggled back on."""
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    for artist in tool.artists:
        if getattr(artist, '_mt_group', None) == 'test.early':
            artist.set_visible(False)
    plt.gca().set_xlim(date2num([_when(1), _when(5)]))
    assert set(_legend_labels(tool)) == {'test.early', 'test.late'}


def test_hidden_legend_stays_hidden_on_zoom(tmp_path):
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    tool.legend.set_visible(False)
    plt.gca().set_xlim(date2num([_when(1), _when(5)]))
    assert tool.legend is not None
    assert not tool.legend.get_visible()


def test_axvline_is_in_view_by_x_only(tmp_path):
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    axis = plt.gca()
    x = date2num(_when(3))
    line = axis.axvline(x, label='event')
    axis.set_ylim(20, 100)
    assert tool._artist_in_view(line, x - 1, x + 1, 20, 100)
    assert not tool._artist_in_view(line, x + 1, x + 2, 20, 100)


def test_bar_is_in_view_by_its_extent(tmp_path):
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    bars = plt.gca().bar([10], [5], width=2)
    assert tool._artist_in_view(bars, 0, 10.5, 0, 1)
    assert tool._artist_in_view(bars[0], 10.5, 20, 0, 1)
    assert not tool._artist_in_view(bars, 12, 20, 0, 1)


def test_series_match_on_plot_type_as_well_as_group(tmp_path):
    """Overlays can reuse a group name; only the same plot type counts."""
    path = tmp_path / 'legend.log'
    path.write_text(LOG)
    tool = _plot(path)
    axis = plt.gca()
    handle = next(a for a in tool.artists
                  if getattr(a, '_mt_group', None) == 'test.early')
    other = axis.plot([date2num(_when(4))], [50])[0]
    other._mt_group = 'test.early'
    other._mt_plot_type = object()
    tool.artists.append(other)
    xmin, xmax = date2num([_when(3, 30), _when(5)])
    assert not tool._series_in_view(handle, xmin, xmax, 0, 100)
