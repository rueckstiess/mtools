import io
import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
from mtools.mplotqueries.plottypes.base_type import BasePlotType, PALETTES
from mtools.mplotqueries.plottypes.event_type import RSStatePlotType


@pytest.fixture(autouse=True)
def _restore_palette():
    yield
    BasePlotType.use_palette('default')


@pytest.fixture(autouse=True)
def _stdin_is_a_tty(monkeypatch):
    """Constructor must not try to read pytest's captured stdin."""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


def _install_plot_date():
    """Scatter plots call plot_date, which Matplotlib 3.9 removed."""
    if hasattr(plt.Axes, 'plot_date'):
        return

    def plot_date(self, x, y, *args, **kwargs):
        kwargs.setdefault('linestyle', 'None')
        kwargs.setdefault('marker', 'o')
        return self.plot(x, y, *args, **kwargs)

    plt.Axes.plot_date = plot_date


def _hex(color):
    return mcolors.to_hex(color).upper()


def test_named_palette_then_next_marker():
    BasePlotType.use_palette('ibm')
    colors = []
    markers = []
    for index in range(6):
        color, marker = BasePlotType.color_map(str(index))
        colors.append(color)
        markers.append(marker)
    assert colors[:5] == PALETTES['ibm']
    assert colors[5] == PALETTES['ibm'][0]
    assert markers[:5] == ['o'] * 5
    assert markers[5] == 's'


def test_explicit_colors_replace_the_palette():
    BasePlotType.use_palette('ibm', ['#abc', 'tab:red'])
    first, _ = BasePlotType.color_map('a')
    second, _ = BasePlotType.color_map('b')
    assert first == '#ABC'
    assert second == 'tab:red'


def test_invalid_color_exits():
    with pytest.raises(SystemExit):
        BasePlotType.use_palette('default', ['not a color'])


def test_state_plot_keeps_its_own_colors():
    BasePlotType.use_palette('ibm')
    color, _ = RSStatePlotType.color_map('PRIMARY')
    assert color == 'm'
    assert RSStatePlotType.colors[0] == 'm'


LOG = (
    '2019-06-09T02:00:00.000+0000 I COMMAND  [conn1] command test.early '
    'command: find { find: "early", filter: { a: 1 } } '
    'planSummary: IXSCAN keysExamined:1 nreturned:1 5ms\n'
    '2019-06-09T04:00:00.000+0000 I COMMAND  [conn1] command test.late '
    'command: find { find: "late", filter: { a: 1 } } '
    'planSummary: IXSCAN keysExamined:1 nreturned:1 50ms\n'
)


def _plotted_colors(path, *extra):
    _install_plot_date()
    tool = MPlotQueriesTool()
    out = path.parent / 'palette.png'
    tool.run('%s --output-file %s %s' % (path, out, ' '.join(extra)))
    return [_hex(artist.get_color()) for artist in tool.artists]


def test_palette_flag_colors_the_groups(tmp_path):
    path = tmp_path / 'palette.log'
    path.write_text(LOG)
    plotted = _plotted_colors(path, '--palette', 'ibm')
    assert set(plotted) == set(PALETTES['ibm'][:2])


def test_colors_flag_colors_the_groups(tmp_path):
    path = tmp_path / 'palette.log'
    path.write_text(LOG)
    plotted = _plotted_colors(path, '--colors', '#111111', '#222222')
    assert set(plotted) == {'#111111', '#222222'}
