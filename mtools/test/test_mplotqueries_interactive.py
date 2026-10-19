from mtools.mplotqueries.interactive import InteractiveMixin


class _Artist(object):
    """Stand-in for a plotted artist."""

    def __init__(self, alpha=0.5, size=5.0, edge=1.0):
        self.alpha = alpha
        self.size = size
        self.edge = edge
        self.visible = True

    def get_alpha(self):
        return self.alpha

    def set_alpha(self, value):
        self.alpha = value

    def get_markersize(self):
        return self.size

    def set_markersize(self, value):
        self.size = value

    def get_markeredgewidth(self):
        return self.edge

    def set_markeredgewidth(self, value):
        self.edge = value

    def get_visible(self):
        return self.visible

    def set_visible(self, value):
        self.visible = value


class _Host(InteractiveMixin):
    def __init__(self):
        self.artists = [_Artist()]


def test_interactive_methods_stay_on_the_tool():
    """The plot tool still exposes the moved handlers."""
    from mtools.mplotqueries.mplotqueries import MPlotQueriesTool

    assert issubclass(MPlotQueriesTool, InteractiveMixin)
    for name in ('print_shortcuts', 'onpick', 'onpress', 'toggle_artist',
                 'toggle_marker_edges', 'increase_opacity',
                 'decrease_opacity', 'increase_marker_size',
                 'decrease_marker_size'):
        assert callable(getattr(MPlotQueriesTool, name))


def test_opacity_and_marker_size(capsys):
    """Opacity and marker shortcuts still change the artists."""
    host = _Host()
    artist = host.artists[0]
    host.increase_opacity(0.1)
    assert artist.get_alpha() == 0.6
    host.decrease_marker_size()
    assert artist.get_markersize() == 4.0
    host.toggle_marker_edges()
    assert artist.get_markeredgewidth() == 0
    host.toggle_marker_edges()
    assert artist.get_markeredgewidth() == 1.0
    host.print_shortcuts(scatter=True)
    output = capsys.readouterr().out
    assert 'keyboard shortcuts' in output
    assert 'marker edges' in output
