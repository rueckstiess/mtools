from datetime import MAXYEAR, MINYEAR, datetime

from dateutil.tz import tzutc

from mtools.util import OrderedDict
from mtools.util.grouping import Grouping

try:
    from matplotlib import cm
except ImportError as error:
    raise ImportError("Can't import matplotlib. See "
                      "https://matplotlib.org/users/installing.html "
                      "for instructions on how to install matplotlib."
                      "Error: " + str(error))


class BasePlotType(object):

    # 14 most distinguishable colors, according to
    # http://stackoverflow.com/questions/309149/generate-distinctly-different-rgb-colors-in-graphs
    colors = ['#0000FF', '#FF00F6', '#01FFFE', '#505050', '#909090',
              '#FF0000', '#00FF00', '#FFA6FE', '#FFDB66', '#006401',
              '#010067', '#95003A', '#007DB5', '#FFEEE8', '#774D00']

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
