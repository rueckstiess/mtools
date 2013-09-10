from mtools.util import OrderedDict
from mtools.util.log2code import Log2CodeConverter
import re
import types

try:
    from matplotlib import cm
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")

class BasePlotType(object):

    # 16 most distinguishable colors, according to 
    # http://stackoverflow.com/questions/309149/generate-distinctly-different-rgb-colors-in-graphs
    colors = ['#000000','#00FF00','#0000FF','#FF0000','#01FFFE','#FFA6FE','#FFDB66','#006401', \
              '#010067','#95003A','#007DB5','#FF00F6','#FFEEE8','#774D00','#90FB92','#0076FF']
    color_index = 0
    markers = ['o', 's', '<', 'D']
    marker_index = 0

    sort_order = 0
    plot_type_str = 'base'
    default_group_by = None

    # set group_by in sub-classes to force a group_by as below
    # group_by = 'example'

    def __init__(self, args=None, unknown_args=None):
        self.args = args
        self.unknown_args = unknown_args
        self.groups = OrderedDict()
        self.empty = True
        self.limits = None

    def accept_line(self, logline):
        """ return True if this PlotType can plot this line. """
        return True

    def add_line(self, logline):
        """ append log line to this plot type. """
        key = None
        self.empty = False
        self.groups.setdefault(key, list()).append(logline)

    @property 
    def loglines(self):
        """ iterator yielding all loglines from groups dictionary. """
        for key in self.groups:
            for logline in self.groups[key]:
                yield logline

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
        """ (re-)group all loglines by the given group. """
        if hasattr(self, 'group_by'):
            group_by = self.group_by
        else:
            group_by = self.default_group_by
            if self.args['group'] != None:
                group_by = self.args['group']
        
        groups = OrderedDict()

        for logline in self.loglines:
            # if group_by is a function, call on logline
            if hasattr(group_by, '__call__'):
                key = group_by(logline)
            # if the logline has attribute of group_by, use that as key
            elif group_by and hasattr(logline, group_by):
                key = getattr(logline, group_by)
            # if the PlotType has a method with the name of group_by call that on logline
            elif group_by and hasattr(self, group_by):
                f = getattr(self, group_by)
                key = f(logline)
            # if a --label was given, use that as key
            # elif self.args and self.args['label']:
            #     key = self.args['label']
            # else key is None
            else:
                key = None
                # try to match as regular expression
                if type(group_by) == types.StringType:
                    match = re.search(group_by, logline.line_str)
                    if match:
                        if len(match.groups()) > 0:
                            key = match.group(1)
                        else:
                            key = match.group()

            # special case: group together all connections
            # if group_by == "thread" and key and key.startswith("conn"):
            #     key = "conn####"

            groups.setdefault(key, list()).append(logline)
        
        # sort groups by number of data points
        groups = OrderedDict( sorted(groups.iteritems(), key=lambda x: len(x[1]), reverse=True) )

        # if --group-limit is provided, combine remaining groups
        if self.args['group_limit']:

            # now group together all groups that did not make the limit
            groups['other'] = []
            # only go to second last (-1), since the 'other' group is now last
            for other_group in groups.keys()[ self.args['group_limit']:-1 ]:
                groups['other'].extend(groups[other_group])
                del groups[other_group]

        self.groups = groups

    def plot_group(self, group, idx, axis):
        raise NotImplementedError("BasePlotType can't plot. Use a derived class instead")

    def plot(self, axis, ith_plot, total_plots, limits):
        self.limits = limits

        artists = []
        print self.plot_type_str.upper(), "plot"
        print "%5s %9s  %s"%("id", " #points", "group")

        for idx, group in enumerate(self.groups):
            print "%5s %9s  %s"%(idx+1, len(self.groups[group]), group)
            group_artists = self.plot_group(group, idx+ith_plot, axis)
            if isinstance(group_artists, list):
                artists.extend(group_artists)
            else:
                artists.append(group_artists)

        print

        return artists

