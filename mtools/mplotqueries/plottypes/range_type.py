import argparse
from datetime import timedelta

from mtools.mplotqueries.plottypes.base_type import BasePlotType
from mtools.util.log2code import Log2CodeConverter

try:
    from matplotlib.dates import date2num, num2date
except ImportError as error:
    raise ImportError("Can't import matplotlib. See "
                      "https://matplotlib.org/users/installing.html "
                      "for instructions on how to install matplotlib."
                      "Error: " + str(error))


class RangePlotType(BasePlotType):

    plot_type_str = 'range'
    sort_order = 2
    l2cc = Log2CodeConverter()

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        argparser = argparse.ArgumentParser("mplotqueries --type range")
        argparser.add_argument('--gap', action='store', metavar='SEC',
                               type=int, help=("gap threshold in seconds "
                                               "after which a new line is "
                                               "started (default: 60)"),
                               default=None)
        sub_args = vars(argparser.parse_args(unknown_args))

        self.gap = sub_args['gap']

    def accept_line(self, logevent):
        """Return True if the log line does not have a duration."""
        return True

    def log2code(self, logevent):
        codeline = self.l2cc(logevent.line_str)
        if codeline:
            return ' ... '.join(codeline.pattern)
        else:
            return None

    def plot_group(self, group, idx, axis):
        y_min, y_max = axis.get_ylim()

        if y_min == 0. and y_max == 1.:
            axis.set_ylim(0.0, 1.0)

        height = (y_max - y_min) / len(self.groups)
        y_bottom = y_min + (y_max - y_min) - idx * height

        x_lefts = [date2num(self.groups[group][0].datetime)]
        x_rights = []

        if self.gap:
            td = timedelta(seconds=self.gap)
            for le, le_next in zip(self.groups[group][:-1],
                                   self.groups[group][1:]):
                if le_next.datetime - le.datetime >= td:
                    x_lefts.append(date2num(le_next.datetime))
                    x_rights.append(date2num(le.datetime))

        x_rights.append(date2num(self.groups[group][-1].datetime))

        color = self.colors[idx % len(self.colors)]

        artists = []

        for x_left, x_right in zip(x_lefts, x_rights):
            width = max(0.0001, x_right - x_left)
            artist = axis.barh(y_bottom - 0.5 * height, width=width,
                               height=0.7 * height, left=x_left, color=color,
                               alpha=0.8, edgecolor='white', picker=5,
                               linewidth=1, align='center')[0]

            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_left = x_left
            artist._mt_right = x_right

            artists.append(artist)

        if len(self.groups) < 50:
            axis.annotate(group, xy=(0, y_bottom - height / 2.),
                          xycoords='axes fraction', xytext=(-10, 0),
                          textcoords='offset pixels', va='bottom',
                          ha='right', fontsize=9)

        axis.axes.get_yaxis().set_visible(False)

        return artists

    def clicked(self, event):
        # group = event.artist._mt_group
        print(num2date(event.artist._mt_left).strftime("%a %b %d %H:%M:%S") +
              ' - ' +
              num2date(event.artist._mt_right).strftime("%a %b %d %H:%M:%S"))
