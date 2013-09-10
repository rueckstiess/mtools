from mtools.mplotqueries.plottypes.base_type import BasePlotType
from datetime import timedelta
import argparse

try:
    from matplotlib.dates import date2num, num2date
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")
    
from mtools.util.log2code import Log2CodeConverter

class RangePlotType(BasePlotType):

    plot_type_str = 'range'
    sort_order = 2
    l2cc = Log2CodeConverter()

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        self.argparser = argparse.ArgumentParser("mplotqueries --type range")
        self.argparser.add_argument('--gap', action='store', metavar='SEC', type=int, help="gap threshold in seconds after which a new line is started (default: 60)", default=None)
        sub_args = vars(self.argparser.parse_args(unknown_args))

        self.gap = sub_args['gap']


    def accept_line(self, logline):
        """ return True if the log line does not have a duration. """
        return True

    def log2code(self, logline):
        codeline = self.l2cc(logline.line_str)
        if codeline:
            return ' ... '.join(codeline.pattern)
        else:
            return None

    def plot_group(self, group, idx, axis):
        y_min, y_max = axis.get_ylim()

        if y_min == 0. and y_max == 1.:
            axis.set_ylim(0.0, 1.0)

        height = (y_max - y_min) / len(self.groups)
        y_bottom = y_min + (y_max-y_min) - idx * height

        x_lefts = [ date2num( self.groups[group][0].datetime ) ]
        x_rights = []

        if self.gap:
            td = timedelta(seconds=self.gap)
            for ll, ll_next in zip(self.groups[group][:-1], self.groups[group][1:]):
                if ll_next.datetime - ll.datetime >= td:
                    x_lefts.append( date2num(ll_next.datetime) )
                    x_rights.append( date2num(ll.datetime) )

        x_rights.append( date2num( self.groups[group][-1].datetime ) )

        color=self.colors[idx%len(self.colors)]
        
        artists = []

        for x_left, x_right in zip(x_lefts, x_rights):
            artist = axis.barh(y_bottom-0.5*height, x_right-x_left, height=0.7*height, left=x_left, color=color, alpha=0.7, edgecolor='white', picker=5, linewidth=1, align='center')[0]
            
            if group:
                if len(self.groups) < 50:
                    axis.text(x_right, y_bottom-0.5*height, group + '   ', verticalalignment='center', horizontalalignment='right', color=color, fontsize=9)

            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_left = x_left
            artist._mt_right = x_right

            artists.append(artist)

        return artists

    def print_line(self, event):
        group = event.artist._mt_group
        print num2date(event.artist._mt_left).strftime("%a %b %d %H:%M:%S"), '-', num2date(event.artist._mt_right).strftime("%a %b %d %H:%M:%S")


