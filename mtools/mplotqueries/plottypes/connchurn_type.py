import argparse
import re

import numpy as np

from mtools.mplotqueries.plottypes.base_type import BasePlotType

try:
    from matplotlib.dates import date2num, num2date
except ImportError as error:
    raise ImportError("Can't import matplotlib. See "
                      "https://matplotlib.org/users/installing.html "
                      "for instructions on how to install matplotlib."
                      "Error: " + str(error))


def opened_closed(logevent):
    """
    Inspect a log line and groups it by connection being openend or closed.

    If neither, return False.
    """
    if "connection accepted" in logevent.line_str:
        return "opened"
    elif "end connection" in logevent.line_str:
        return "closed"
    else:
        return False


class ConnectionChurnPlotType(BasePlotType):
    """
    Plot a histogram plot over all logevents.

    The bucket size can be specified with the --bucketsize or -b parameter.
    Unit is in seconds.
    """

    plot_type_str = 'connchurn'
    timeunits = {'sec': 1, 's': 1, 'min': 60, 'm': 1, 'hour': 3600,
                 'h': 3600, 'day': 86400, 'd': 86400}
    sort_order = 1

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        argparser = argparse.ArgumentParser("mplotqueries --type histogram")
        argparser.add_argument('--bucketsize', '-b', action='store',
                               metavar='SIZE',
                               help="histogram bucket size in seconds",
                               default=60)
        sub_args = vars(argparser.parse_args(unknown_args))

        self.logscale = args['logscale']
        # get bucket size, either as int (seconds) or as string
        # (see timeunits above)
        bs = sub_args['bucketsize']
        try:
            self.bucketsize = int(bs)
        except ValueError:
            self.bucketsize = self.timeunits[bs]

        self.ylabel = "# connections opened/closed"

        self.group_by = opened_closed

    def accept_line(self, logevent):
        """Only return lines with 'connection accepted' or 'end connection'."""
        return opened_closed(logevent)

    def plot_group(self, group, idx, axis):

        x = date2num([logevent.datetime for logevent in self.groups[group]])
        color, _ = self.color_map(group)

        xmin, xmax = date2num(self.limits)
        n_bins = max(1, int((xmax - xmin) * 24. * 60. * 60. / self.bucketsize))
        if n_bins > 1000:
            # warning for too many buckets
            print("warning: %i buckets, will take a while to render. "
                  "consider increasing --bucketsize." % n_bins)

        bins = np.linspace(xmin, xmax, n_bins)

        n, bins, artists = axis.hist(x, bins=bins, align='mid',
                                     log=self.logscale, histtype="bar",
                                     color=color, edgecolor="white",
                                     alpha=0.8, picker=True,
                                     label="# connections %s per bin" % group)

        if group == 'closed':
            ymin = 0
            for a in artists:
                height = a.get_height()
                height = -height
                a.set_height(height)
                if height < ymin:
                    ymin = height

            axis.set_ylim(bottom=ymin * 1.1)

        elif group == 'opened':
            self.ymax = max([a.get_height() for a in artists])

        for num_conn, bin, artist in zip(n, bins, artists):
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_n = num_conn
            artist._mt_bin = bin

        return artists

    def plot_total_conns(self, axis):
        opened = self.groups['opened']
        closed = self.groups['closed']

        total = sorted(opened + closed, key=lambda le: le.datetime)
        x = date2num([logevent.datetime for logevent in total])

        try:
            conns = [int(re.search(r'(\d+) connections? now open',
                                   le.line_str).group(1)) for le in total]
        except AttributeError:
            # hack, v2.0.x doesn't have this information
            axis.set_ylim(top=self.ymax * 1.1)
            return

        axis.plot(x, conns, '-', color='black', linewidth=2, alpha=0.8,
                  label='# open connections total')

        self.ymax = max(self.ymax, max(conns))
        axis.set_ylim(top=self.ymax * 1.1)

    def plot(self, axis, ith_plot, total_plots, limits):
        artists = BasePlotType.plot(self, axis, ith_plot, total_plots, limits)

        # parse all groups and plot currently open number of connections
        artist = self.plot_total_conns(axis)
        artists.append(artist)

        return artists

    @classmethod
    def color_map(cls, group):
        """
        Change default color behavior.

        Map certain states always to the same colors (similar to MMS).
        """
        colors = {'opened': 'green', 'closed': 'red', 'total': 'black'}
        return colors[group], cls.markers[0]

    def clicked(self, event):
        """Print group name and number of items in bin."""
        group = event.artist._mt_group
        n = event.artist._mt_n
        dt = num2date(event.artist._mt_bin)
        print("%4i connections %s in %s sec beginning at %s"
              % (n, group, self.bucketsize, dt.strftime("%b %d %H:%M:%S")))
