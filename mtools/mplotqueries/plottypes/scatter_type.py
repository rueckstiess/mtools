from mtools.mplotqueries.plottypes.base_type import BasePlotType
from operator import itemgetter
from datetime import timedelta

import argparse

try:
    import matplotlib.pyplot as plt

    from matplotlib.dates import date2num
    from matplotlib.lines import Line2D
    from matplotlib.patches import Polygon

except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


class ScatterPlotType(BasePlotType):

    plot_type_str = 'scatter'
    sort_order = 3
    default_group_by = 'namespace'

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        self.logscale = args['logscale']

        # parse arguments further to get --yaxis argument
        argparser = argparse.ArgumentParser("mplotqueries --type scatter")
        argparser.add_argument('--yaxis', '-y', action='store', metavar='FIELD', default='duration')
        args = vars(argparser.parse_args(unknown_args))

        self.field = args['yaxis']
        if args['yaxis'] == 'duration':
            self.ylabel = 'duration in ms'
        else:
            self.ylabel = args['yaxis']

        self.durlines = []


    def accept_line(self, logevent):
        """ return True if the log line has the nominated yaxis field. """
        return (getattr(logevent, self.field) != None)

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ getattr(logevent, self.field) for logevent in self.groups[group] ]
        
        if self.logscale:
            axis.semilogy()

        artist = axis.plot_date(x, y, color=color, markeredgecolor='k', marker=marker, alpha=0.7, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist

    def clicked(self, event):
        """ this is called if an element of this plottype was clicked. Implement in sub class. """        
        group = event.artist._mt_group
        indices = event.ind

        if not event.mouseevent.dblclick:
            for i in indices:
                print self.groups[group][i].line_str

        else:
            # toggle durline
            first = indices[0]
            logevent = self.groups[group][first]

            try:
                # remove triangle for this event
                idx = map(itemgetter(0), self.durlines).index(logevent)
                _, poly = self.durlines[idx]
                poly.remove()
                plt.gcf().canvas.draw()
                del self.durlines[idx]

            except ValueError:
                # construct triangle and add to list of durlines
                pts = [ [date2num(logevent.datetime), 0], 
                        [date2num(logevent.datetime), logevent.duration], 
                        [date2num(logevent.datetime - timedelta(milliseconds=logevent.duration)), 0] ]

                poly = Polygon(pts, closed=True, alpha=0.2, linewidth=0, facecolor=event.artist.get_markerfacecolor(), edgecolor=None, zorder=-10000)

                ax = plt.gca()
                ax.add_patch(poly)
                plt.gcf().canvas.draw()

                self.durlines.append( (logevent, poly) )



class DurationLineType(ScatterPlotType):

    plot_type_str = 'durline'
    sort_order = 3
    default_group_by = 'namespace'

    def __init__(self, args=None, unknown_args=None):
        ScatterPlotType.__init__(self, args, unknown_args)
        self.args['optime_start'] = True

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x_start = date2num( [ logevent.datetime for logevent in self.groups[group] ] )
        x_end = date2num( [ logevent.end_datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        y = [ getattr(logevent, 'duration') for logevent in self.groups[group] ]
        
        if self.logscale:
            axis.semilogy()

        # artist = axis.plot_date(x, y, color=color, markeredgecolor='k', marker=marker, alpha=0.7, \
        #     markersize=7, picker=5, label=group)[0]
        
        artists = []
        labels = set()

        for i, (xs, xe, ye) in enumerate(zip(x_start, x_end, y)):
            artist = axis.plot_date([xs, xe], [0, ye], '-', color=color, alpha=0.7, linewidth=2,
            markersize=7, picker=5, label=None if group in labels else group)[0]
            
            labels.add(group)

            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group 
            artist._mt_line_id = i
            artists.append(artist)

        return artists


    def clicked(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print self.groups[group][line_id].line_str



class NScannedNPlotType(ScatterPlotType):

    plot_type_str = 'nscanned/n'
    default_group_by = 'namespace'


    def __init__(self, args=None, unknown_args=None):
        # Only call baseplot type constructor, we don't need argparser
        BasePlotType.__init__(self, args, unknown_args)

        self.ylabel = 'nscanned / n ratio'

    def accept_line(self, logevent):
        """ return True if the log line has a duration. """
        return getattr(logevent, 'nscanned') and getattr(logevent, 'nreturned')

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logevent.datetime for logevent in self.groups[group] ] )

        color, marker = self.color_map(group)

        # duration plots require y coordinate and use plot_date
        nreturned = float(logevent.nreturned)
        if nreturned == 0.0:
            nreturned = 1.0

        y = [ getattr(logevent, 'nscanned') / nreturned for logevent in self.groups[group] ]
        artist = axis.plot_date(x, y, color=color, marker=marker, alpha=0.5, \
            markersize=7, picker=5, label=group)[0]
        # add meta-data for picking
        artist._mt_plot_type = self
        artist._mt_group = group 

        return artist




