from base_type import BasePlotType

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")
    
class EventPlotType(BasePlotType):

    plot_type_str = 'event'

    def plot_group(self, group, idx, axis):
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        # event plots use axvline
        artists = []
        color, marker = self.color_map(group)

        for i, xcoord in enumerate(x):
            if i == 0:
                artist = axis.axvline(xcoord, linewidth=2, picker=5, color=color, alpha=0.6, label=group)
            else:
                artist = axis.axvline(xcoord, linewidth=2, picker=5, color=color, alpha=0.6)
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_line_id = i
            artists.append(artist)

        axis.autoscale_view(scaley=False)
        return artists

    def print_line(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print self.groups[group][line_id].line_str
