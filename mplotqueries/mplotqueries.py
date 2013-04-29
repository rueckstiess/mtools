#!/usr/bin/python

import argparse
import re
import os
import sys
import uuid
import glob
import matplotlib.pyplot as plt
import cPickle

from mtools.mtoolbox.logline import LogLine
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.dates import date2num, DateFormatter
from collections import OrderedDict



class BasePlotType(object):

    can_group_by = [None]
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    markers = ['o', 's', '<', 'D']

    plot_type_str = 'base'

    def __init__(self):
        self.groups = OrderedDict()

    def accept_line(self, logline):
        """ return True if this PlotType can plot this line. """
        return True

    def add_line(self, logline):
        """ append log line to this plot type. """
        key = 'ungrouped'
        self.groups.setdefault(key, list()).append(logline)

    @property 
    def loglines(self):
        """ iterator yielding all loglines from groups dictionary. """
        for key in self.groups:
            for logline in self.groups[key]:
                yield logline

    def group_by(self, group_by):
        """ (re-)group all loglines by the given group. """

        # check if this PlotType can group by given group 
        if group_by not in self.can_group_by:
            return False

        groups = OrderedDict()

        for logline in self.loglines:
            key = getattr(logline, group_by)
            
            # convert None to string
            if key == None:
                key = "None"

            # special case: group together all connections
            if group_by == "thread" and key.startswith("conn"):
                key = "conn####"

            groups.setdefault(key, list()).append(logline)
        
        self.groups = groups

    def plot_group(self, group, idx, axis):
        pass

    def plot(self, axis):
        artists = []
        print self.plot_type_str.upper()
        print "%5s %9s  %s"%("id", " #points", "group")

        for idx, group in enumerate(self.groups):
            print "%5s %9s  %s"%(idx+1, len(self.groups[group]), group)
            group_artists = self.plot_group(group, idx, axis)
            if isinstance(group_artists, list):
                artists.extend(group_artists)
            else:
                artists.append(group_artists)

        print

        return artists



class DurationPlotType(BasePlotType):

    can_group_by = ['namespace', 'operation', 'thread', 'none']
    plot_type_str = 'duration'

    def accept_line(self, logline):
        """ return True if the log line has a duration. """
        return logline.duration

    def plot_group(self, group, idx, axis):
        # create x-coordinates for all log lines in this group
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        # duration plots require y coordinate and use plot_date
        y = [ logline.duration for logline in self.groups[group] ]
        artist = plt.plot_date(x, y, color=self.colors[idx%len(self.colors)], \
            marker=self.markers[(idx / 7) % len(self.markers)], alpha=0.5, \
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


class EventPlotType(BasePlotType):

    can_group_by = ['none']
    plot_type_str = 'event'

    def accept_line(self, logline):
        """ return True if the log line does not have a duration. """
        return not logline.duration

    def plot_group(self, group, idx, axis):
        x = date2num( [ logline.datetime for logline in self.groups[group] ] )

        # event plots use axvline
        artists = []
        for i, xcoord in enumerate(x):
            artist = plt.gca().axvline(xcoord, linewidth=1, picker=5, color=[0.8, 0.8, 0.8])
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_line_id = i
            artists.append(artist)

        return artists

    def print_line(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print self.groups[group][line_id].line_str



class MongoPlotQueries(object):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        self.plot_types = {'duration': DurationPlotType, 'event': EventPlotType}

        self.parseArgs()

        # create PlotType instances
        self.plot_instances = [self.plot_types[t]() for t in set(self.args['type'])]

        self._parse_loglines()
        
        self._group()

        if self.args['overlay'] == 'reset':
            self._remove_overlays()

        # if --overlay is set, save groups in a file, else load groups and plot
        if self.args['overlay'] == "list":
            self._list_overlays()
            raise SystemExit
        elif self.args['overlay'] == "" or self.args['overlay'] == "add":
            self._save_overlay()
            raise SystemExit

        plot_specified = not sys.stdin.isatty() or len(self.args['filename']) > 0

        # if no plot is specified (either pipe or filename(s)) and reset, quit now
        if not plot_specified and self.args['overlay'] == 'reset':
            raise SystemExit

        # else plot (with potential overlays) if there is something to plot
        groups_loaded = self._load_overlays()
        if plot_specified or groups_loaded:
            self.plot()
        else:
            print "Nothing to plot."
            raise SystemExit


    def parseArgs(self):
        # create parser object
        parser = argparse.ArgumentParser(description='A script to plot query durations in a logfile' \
            ' (requires numpy and matplotlib packages). Clicking on any of the plot points will print' \
            ' the corresponding log line to stdout. Clicking on the x-axis labels will output an ' \
            ' "mlogfilter" string with the matching "--from" parameter.')
        
        parser.usage = "mplotqueries [-h] filename\n                    [--ns [NS [NS ...]]] [--log]\n                    [--exclude-ns [NS [NS ...]]]\n"

        # positional argument
        if sys.stdin.isatty():
            parser.add_argument('filename', action='store', nargs="*", help='logfile(s) to parse')
        
        parser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
        parser.add_argument('--log', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        parser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')
        parser.add_argument('--no-legend', action='store_true', default=False, help='turn off legend (default=on)')
        parser.add_argument('--group', action='store', default='namespace', choices=['namespace', 'operation', 'thread'], 
            help="group by namespace (default), operation or thread.")
        parser.add_argument('--overlay', action='store', nargs='?', default=None, const='add', choices=['add', 'list', 'reset'], help="overlays allow for several plots to be combined. Use --overlay (or --overlay add) to add a new overlay. Use --overlay list to show existing overlays. Use --overlay reset to delete all overlays. A call without --overlay will add all overlays to the current plot.")
        parser.add_argument('--type', action='store', default=['duration'], nargs='+', choices=['duration', 'event', 'range'])
        # parser.add_argument('--no-duration', action='store_true', default=False, help="plots vertical lines for log lines that don't have a duration. By default, log lines without a duration are skipped.")

        self.args = vars(parser.parse_args())


    def _onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """
        if isinstance(event.artist, Line2D):
            # only print loglines of visible points
            if not event.artist.get_visible():
                return

            # get PlotType and let it print that event
            plot_type = event.artist._mt_plot_type
            plot_type.print_line(event)

        elif isinstance(event.artist, Text):
            text = event.artist
            # output mlogfilter output
            time_str = text.get_text().replace('\n', ' ')
            file_name = self.args['filename'] if 'filename' in self.args else ''
            print "mlogfilter %s --from %s"%(file_name, time_str)


    def _toggle_artist(self, idx):
        try:
            visible = self.artists[idx].get_visible()
            self.artists[idx].set_visible(not visible)
            plt.gcf().canvas.draw()
        except IndexError:
            pass


    def _onpress(self, event):
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key)-1
            self._toggle_artist(idx)

        if event.key == '0':
            visible = any([a.get_visible() for a in self.artists])
            for artist in self.artists:
                artist.set_visible(not visible)
            
            plt.gcf().canvas.draw()

        if event.key == 'q':
            raise SystemExit('quitting.')


    def _parse_loglines(self):
        # open logfile(s)
        if sys.stdin.isatty():
            logfiles = ( open(f, 'r') for f in self.args['filename'] )
        else:
            logfiles = [sys.stdin]

        for logfile in logfiles:
            for line in logfile:

                # create LogLine object
                logline = LogLine(line)

                # only add if namespace is not excluded
                if logline.namespace == None:
                    logline._namespace = "None"

                if self.args['ns'] != None and logline.namespace not in self.args['ns']:
                    continue

                if self.args['exclude_ns'] != None and (logline.namespace in self.args['exclude_ns']):
                    continue

                # if logline doesn't have datetime, skip
                if logline.datetime == None:
                    continue

                # offer to each PlotType and see if it can plot it
                line_accepted = False
                for plot_inst in self.plot_instances:
                    if plot_inst.accept_line(logline):
                        line_accepted = True
                        plot_inst.add_line(logline)

        # close files after parsing
        if sys.stdin.isatty():
            for f in logfiles:
                f.close()


    def _group(self):
        for plot_inst in self.plot_instances:
            plot_inst.group_by(self.args['group'])

    
    def _list_overlays(self):
        group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(group_path):
            return

        # load groups and merge
        group_files = glob.glob(os.path.join(group_path, '*'))
        print "Existing overlays:"
        for f in group_files:
            print "  ", os.path.basename(f)


    # def _save_overlay(self):
    #     # make directory if not present
    #     group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
    #     if not os.path.exists(group_path):
    #         try:
    #             os.makedirs(group_path)
    #         except OSError:
    #             SystemExit("Couldn't create directory %s, quitting. Check permissions, or run without --overlay to display directly." % group_path)

    #     # create unique filename
    #     while True:
    #         uid = str(uuid.uuid4())[:8]
    #         group_file = os.path.join(group_path, uid)
    #         if not os.path.exists(group_file):
    #             break

    #     # dump groups and handle exceptions
    #     try:
    #         cPickle.dump(self.groups, open(group_file, 'wb'), -1)
    #         print "Created overlay: %s" % uid
    #     except Exception as e:
    #         print "Error: %s" % e
    #         SystemExit("Couldn't write to %s, quitting. Check permissions, or run without --overlay to display directly." % group_file)


    def _load_overlays(self):
        pass
    #     group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
    #     if not os.path.exists(group_path):
    #         return False

    #     # load groups and merge
    #     group_files = glob.glob(os.path.join(group_path, '*'))
    #     for f in group_files:
    #         try:
    #             group_dict = cPickle.load(open(f, 'rb'))
    #         except Exception as e:
    #             print "Couldn't read overlay %s, skipping." % f
    #             continue

    #         # extend each list according to its key
    #         for key in group_dict:
    #             self.groups.setdefault(key, list()).extend(group_dict[key])
            
    #         print "Loaded overlay: %s" % os.path.basename(f)
        
    #     if len(group_files) > 0:
    #         print

    #     return len(group_files) > 0


    def _remove_overlays(self):
        group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(group_path):
            return 0

        group_files = glob.glob(os.path.join(group_path, '*'))
        # remove all group files
        for f in group_files:
            try:
                os.remove(f)
            except OSError as e:
                print "Error occured when deleting %s, skipping."
                continue

        if len(group_files) > 0:
            print "Deleted overlays."          


    def _print_shortcuts(self):
        print "keyboard shortcuts (focus must be on figure window):"
        print "%5s  %s" % ("1-9", "toggle visibility of individual plots 1-9")
        print "%5s  %s" % ("0", "toggle visibility of all plots")
        print "%5s  %s" % ("q", "quit mplotqueries")



    def plot(self):
        self.artists = []
        axis = plt.subplot(111)

        for plot_inst in self.plot_instances:
            self.artists.extend(plot_inst.plot(axis))
            
        self._print_shortcuts()

        axis.set_xlabel('time')
        axis.set_xticklabels(axis.get_xticks(), rotation=90, fontsize=10)
        axis.xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))

        for label in axis.get_xticklabels():  # make the xtick labels pickable
            label.set_picker(True)

        # log y axis
        if self.args['log']:
            axis.set_yscale('log')
            axis.set_ylabel('query duration in ms (log scale)')
        else:
            axis.set_ylabel('query duration in ms')

        if not self.args['no_legend']:
            handles, labels = axis.get_legend_handles_labels()
            if len(labels) > 0:
                self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1, fontsize=9)

        plt.gcf().canvas.mpl_connect('pick_event', self._onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self._onpress)

        plt.show()


if __name__ == '__main__':
    mplotqueries = MongoPlotQueries()

