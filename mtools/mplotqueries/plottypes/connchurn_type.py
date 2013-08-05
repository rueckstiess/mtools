from mtools.mplotqueries.plottypes.base_type import BasePlotType
import argparse
import types
import re
import numpy as np

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


from mtools.util.log2code import Log2CodeConverter


class ConnectionChurnPlotType(BasePlotType):
    """ plots a histogram plot over all loglines. The bucket size can be specified with the --bucketsize or -b parameter. Unit is in seconds. """

    plot_type_str = 'connchurn'
    timeunits = {'sec':1, 's':1, 'min':60, 'm':1, 'hour':3600, 'h':3600, 'day':86400, 'd':86400}
    sort_order = 1

    group_by = 'opened_closed'


    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        self.argparser = argparse.ArgumentParser("mplotqueries --type histogram")
        self.argparser.add_argument('--bucketsize', '-b', action='store', metavar='SIZE', help="histogram bucket size in seconds", default=60)
        sub_args = vars(self.argparser.parse_args(unknown_args))

        self.logscale = args['logscale']
        # get bucket size, either as int (seconds) or as string (see timeunits above)
        bs = sub_args['bucketsize']
        try:
            self.bucketsize = int(bs)
        except ValueError:
            self.bucketsize = self.timeunits[bs]

        self.ylabel = "# connections opened/closed"

    def opened_closed(self, logline):
        """ inspects a log line and groups it by connection being openend or closed. If neither, return False. """
        if "connection accepted" in logline.line_str:
            return "opened"
        elif "end connection" in logline.line_str:
            return "closed"
        else:
            return False

    def accept_line(self, logline):
        """ return True for each line. We bucket everything. Filtering has to be done before passing to this type of plot. """
        return self.opened_closed(logline)


    def plot_group(self, group, idx, axis):

        x = date2num( [ logline.datetime for logline in self.groups[group] ] )
        color, _ = self.color_map(group)

        xmin, xmax = date2num(self.limits)
        n_bins = (xmax - xmin)*24.*60.*60./self.bucketsize

        bins = np.linspace(xmin, xmax, n_bins)

        n, bins, artists = axis.hist(x, bins=bins, rwidth=1, align='mid', log=self.logscale, histtype="bar", color=color, 
            edgecolor="white", alpha=0.65, picker=True, label="# connections %s per bin" % group)

        if group == 'closed':
            ymin = 0
            for a in artists:
                    height = a.get_height()
                    height = -height
                    a.set_height(height)
                    if height < ymin: 
                        ymin = height
        
            axis.set_ylim(bottom = ymin*1.1) 
        
        elif group == 'opened':
            self.ymax = max([a.get_height() for a in artists])

        return artists


    def plot_total_conns(self, axis):
        opened = self.groups['opened']
        closed = self.groups['closed']

        total = sorted(opened+closed, key=lambda ll: ll.datetime)
        x = date2num( [ logline.datetime for logline in total ] )
        conns = [int(re.search(r'(\d+) connections? now open', ll.line_str).group(1)) for ll in total]

        axis.plot(x, conns, '-', color='black', linewidth=2, alpha=0.7, label='# open connections total')

        self.ymax = max(self.ymax, max(conns))
        axis.set_ylim(top = self.ymax*1.1) 


    def plot(self, axis, ith_plot, total_plots, limits):
        artists = BasePlotType.plot(self, axis, ith_plot, total_plots, limits)

        # parse all groups and plot currently open number of connections
        artist = self.plot_total_conns(axis)
        artists.append(artist)

        return artists


    @classmethod
    def color_map(cls, group):
        """ change default color behavior to map certain states always to the same colors (similar to MMS). """
        colors = {'opened': 'green', 'closed':'red', 'total':'black'}
        return colors[group], cls.markers[0]


    def print_line(self, event):
        """ print group name and number of items in bin. """
        group = event.artist._mt_group
        n = event.artist._mt_n
        print "%4i %s" % (n, group)

