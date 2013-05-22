from base_type import BasePlotType

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")

class DurationPlotType(BasePlotType):

    plot_type_str = 'duration'
    sort_order = 1
    default_group_by = 'namespace'

    def accept_line(self, logline):
        """ return True if the log line has a duration. """
        return logline.duration

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ logline.duration for logline in self.groups[group] ]
        artist = axis.plot_date(x, y, color=color, marker=marker, alpha=0.5, \
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
