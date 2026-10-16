import re
from datetime import MAXYEAR, MINYEAR, datetime

from dateutil.tz import tzutc

from mtools.util import OrderedDict
from mtools.util.grouping import Grouping

try:
    from matplotlib import cm
    from matplotlib.colors import is_color_like
except ImportError as e:
    raise ImportError(f"Can't import matplotlib: {str(e)}\n\n"
                       "For installation instructions, see:\n"
                       "   https://matplotlib.org/stable/users/installing/index.html")


_HEX_COLOR = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def _normalize_color(value):
    """Return a matplotlib color, or exit when the value is not one."""
    text = str(value).strip()
    if _HEX_COLOR.match(text):
        return text.upper()
    if is_color_like(text):
        return text
    raise SystemExit("invalid color %r. Use #RGB, #RRGGBB, or a "
                     "matplotlib color name." % value)


# Okabe-Ito, with black last so the first series is not the same color
# as the axes. Tol muted and the IBM palette are also color-blind safe.
_OKABE_ITO = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2',
              '#D55E00', '#CC79A7', '#000000']
_TOL_MUTED = ['#332288', '#88CCEE', '#44AA99', '#117733', '#999933',
              '#DDCC77', '#CC6677', '#882255', '#AA4499']
_IBM = ['#648FFF', '#785EF0', '#DC267F', '#FE6100', '#FFB000']

# 14 most distinguishable colors, according to
# http://stackoverflow.com/questions/309149/generate-distinctly-different-rgb-colors-in-graphs
_DEFAULT = ['#0000FF', '#FF00F6', '#01FFFE', '#505050', '#909090',
            '#FF0000', '#00FF00', '#FFA6FE', '#FFDB66', '#006401',
            '#010067', '#95003A', '#007DB5', '#FFEEE8', '#774D00']

PALETTES = {
    'default': _DEFAULT,
    'okabe-ito': _OKABE_ITO,
    'tol': _TOL_MUTED,
    'ibm': _IBM,
}


class BasePlotType(object):

    colors = list(_DEFAULT)

    color_index = 0
    markers = ['o', 's', '<', 'D']
    marker_index = 0

    sort_order = 0
    plot_type_str = 'base'
    default_group_by = None
    date_range = (datetime(MAXYEAR, 12, 31, tzinfo=tzutc()),
                  datetime(MINYEAR, 1, 1, tzinfo=tzutc()))

    def __init__(self, args=None, unknown_args=None):
        self.args = args
        self.unknown_args = unknown_args
        self.groups = OrderedDict()
        self.empty = True
        self.limits = None

        if self.args['optime_start']:
            self.xlabel = 'time (start of ops)'
        else:
            self.xlabel = 'time (end of ops)'

    @classmethod
    def use_palette(cls, name='default', colors=None):
        """Select the color sequence for plots that color groups in order.

        ``colors`` replaces the named palette. Replica-set state and
        connection-churn plots keep the fixed color they assign per state.
        """
        if colors:
            chosen = [_normalize_color(color) for color in colors]
        else:
            try:
                chosen = PALETTES[name]
            except KeyError:
                known = ', '.join(sorted(PALETTES))
                raise SystemExit("unknown palette %r. Choose from %s."
                                 % (name, known))
        if not chosen:
            raise SystemExit('at least one color is required.')
        # Groups read this list from the base class. A subclass that
        # already plotted may have stored the cycle counter on itself.
        BasePlotType.colors = list(chosen)
        BasePlotType._reset_color_cycle()

    @classmethod
    def _reset_color_cycle(cls):
        """Clear per-class counters so the next plot starts at color zero.

        ``color_map`` stores the advanced counter on the class that
        plotted. An overlay such as ``nscanned/n`` then reads that
        parent counter. A zero stored on the overlay would start it
        over at the first color.
        """
        if cls is BasePlotType:
            cls.color_index = 0
            cls.marker_index = 0
        else:
            for name in ('color_index', 'marker_index'):
                if name in cls.__dict__:
                    delattr(cls, name)
        for subclass in cls.__subclasses__():
            subclass._reset_color_cycle()

    def accept_line(self, logevent):
        """Return True if this PlotType can plot this line."""
        return True

    def add_line(self, logevent):
        """Append log line to this plot type."""
        key = None
        self.empty = False
        self.groups.setdefault(key, list()).append(logevent)

    @property
    def logevents(self):
        """Iterator yielding all logevents from groups dictionary."""
        for key in self.groups:
            for logevent in self.groups[key]:
                try:
                    yield logevent
                except StopIteration:
                    return

    @classmethod
    def color_map(cls, group):
        color = cls.colors[cls.color_index]
        cls.color_index += 1

        marker = cls.markers[cls.marker_index]
        if cls.color_index >= len(cls.colors):
            cls.marker_index += 1
            cls.marker_index %= len(cls.markers)
            cls.color_index %= cls.color_index

        return color, marker

    def group(self):
        """(re-)group all logevents by the given group."""
        if hasattr(self, 'group_by'):
            group_by = self.group_by
        else:
            group_by = self.default_group_by
            if self.args['group'] is not None:
                group_by = self.args['group']

        self.groups = Grouping(self.logevents, group_by)
        self.groups.move_items(None, 'others')
        self.groups.sort_by_size(group_limit=self.args['group_limit'],
                                 discard_others=self.args['no_others'])

    def plot_group(self, group, idx, axis):
        raise NotImplementedError("BasePlotType can't plot. "
                                  "Use a derived class instead")

    def clicked(self, event):
        """
        Call if an element of this plottype was clicked.

        Implement in sub class.
        """
        pass

    def plot(self, axis, ith_plot, total_plots, limits):
        self.limits = limits

        artists = []
        print(self.plot_type_str.upper() + " plot")
        print("%5s %9s  %s" % ("id", " #points", "group"))

        for idx, group in enumerate(self.groups):
            print("%5s %9s  %s" % (idx + 1, len(self.groups[group]), group))
            group_artists = self.plot_group(group, idx + ith_plot, axis)
            if isinstance(group_artists, list):
                artists.extend(group_artists)
            else:
                artists.append(group_artists)

        print()

        return artists
