from mtools.mplotqueries.plottypes.base_type import BasePlotType
import argparse

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


class ScatterPlotType(BasePlotType):

    plot_type_str = 'scatter'
    sort_order = 1
    default_group_by = 'namespace'

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --yaxis argument
        self.argparser = argparse.ArgumentParser("mplotqueries --numeric")
        self.argparser.add_argument('--yaxis', '-y', action='store', metavar='FIELD', default='duration')
        args = vars(self.argparser.parse_args(unknown_args))

        self.field = args['yaxis']
        self.ylabel = args['yaxis']

    def accept_line(self, logline):
        """ return True if the log line has a duration. """
        return getattr(logline, self.field)

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ getattr(logline, self.field) for logline in self.groups[group] ]
        artist = axis.plot_date(x, y, color=color, markeredgecolor='k', marker=marker, alpha=0.5, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist

    def print_line(self, event):
        group = event.artist._mt_group
        indices = event.ind
        for i in indices:
            print self.groups[group][i].line_str


class DurationPlotType(ScatterPlotType):

    plot_type_str = 'duration'
    sort_order = 1
    default_group_by = 'namespace'


    def __init__(self, args=None, unknown_args=None):
        # Only call BasePlotType constructor, we don't need argparser
        BasePlotType.__init__(self, args, unknown_args)
        self.field = 'duration'
        self.ylabel = 'duration in ms'


class NScannedNPlotType(ScatterPlotType):

    plot_type_str = 'nscanned/n'
    sort_order = 1
    default_group_by = 'namespace'


    def __init__(self, args=None, unknown_args=None):
        # Only call baseplot type constructor, we don't need argparser
        BasePlotType.__init__(self, args, unknown_args)

        self.ylabel = 'nscanned / n ratio'

    def accept_line(self, logline):
        """ return True if the log line has a duration. """
        return getattr(logline, 'nscanned') and getattr(logline, 'nreturned')

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ float(getattr(logline, 'nscanned')) / float(getattr(logline, 'nreturned')) for logline in self.groups[group] ]
        artist = axis.plot_date(x, y, color=color, marker=marker, alpha=0.5, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist




