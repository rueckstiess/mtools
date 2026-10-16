import io
import sys

import pytest

from mtools.mplotqueries.overlays import OverlayMixin


@pytest.fixture(autouse=True)
def patch_stdin(monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True


class _Host(OverlayMixin):
    home_path = ''
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self, root):
        self.home_path = root
        self.plot_instances = [{'ns': 'test.a'}]


def test_overlay_methods_stay_on_the_tool():
    from mtools.mplotqueries.mplotqueries import MPlotQueriesTool

    assert issubclass(MPlotQueriesTool, OverlayMixin)
    for name in ('list_overlays', 'save_overlay', 'load_overlays',
                 'remove_overlays'):
        assert callable(getattr(MPlotQueriesTool, name))


def test_overlay_round_trip(tmp_path, capsys):
    host = _Host(str(tmp_path))
    host.save_overlay()
    created = capsys.readouterr().out
    assert 'Created overlay:' in created

    host.plot_instances = []
    assert host.load_overlays() is True
    assert host.plot_instances == [{'ns': 'test.a'}]

    host.list_overlays()
    listed = capsys.readouterr().out
    assert 'Existing overlays:' in listed

    host.remove_overlays()
    assert 'Deleted overlays.' in capsys.readouterr().out
    assert host.load_overlays() is False
