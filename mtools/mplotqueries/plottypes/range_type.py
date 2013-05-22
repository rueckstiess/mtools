from base_type import BasePlotType

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. Try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")

from mtools.util.log2code import Log2CodeConverter

class RangePlotType(BasePlotType):

    plot_type_str = 'range'
    sort_order = 2
    l2cc = Log2CodeConverter()

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

        x_left = date2num( self.groups[group][0].datetime )
        x_right = date2num( self.groups[group][-1].datetime )

        color=self.colors[idx%len(self.colors)]
        if group == None:
            group = " "
        artist = axis.barh(y_bottom-0.5*height, x_right-x_left, height=0.7*height, left=x_left, color=color, alpha=0.4, edgecolor='white', picker=5, linewidth=1, align='center')[0]
        if group:
            if len(self.groups) < 50:
                axis.text(x_right, y_bottom-0.5*height, group + '   ', verticalalignment='center', horizontalalignment='right', color=color, fontsize=9)

        artist._mt_plot_type = self
        artist._mt_group = group
        return artist

    def print_line(self, event):
        group = event.artist._mt_group
        print self.groups[group][0].line_str
        print self.groups[group][-1].line_str


