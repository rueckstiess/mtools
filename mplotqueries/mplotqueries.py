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


class MongoPlotQueries(object):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        self.colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        self.markers = ['o', 's', '<', 'D']
        self.loglines = []
        self.parseArgs()

        self._parse_loglines()

        if self.args['untimed']:
            self._group_untimed()
        else:
            self._group(self.args['group'])

        if self.args['reset']:
            self._remove_overlays()

        # if --overlay is set, save groups in a file, else load groups and plot
        if self.args['overlay']:
            self._save_overlay()
            raise SystemExit

        plot_specified = not sys.stdin.isatty() or len(self.args['filename']) > 0

        # if no plot is specified (either pipe or filename(s)) and reset, quit now
        if not plot_specified and self.args['reset']:
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
        parser.add_argument('--reset', action='store_true', default=False, help="Removes all stored overlays. See --overlay for more information.")
        parser.add_argument('--overlay', action='store_true', default=False, help="plots with this option will be stored as 'overlays' but not plotted. They are all drawn with the first call without --overlay. Use --reset to remove all overlays.")
        parser.add_argument('--untimed', action='store_true', default=False, help="plots vertical lines for each log line, ignoring the duration of the operation.")

        self.args = vars(parser.parse_args())


    def _onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """
        if isinstance(event.artist, Line2D):
            group = event.artist.get_label()

            if not group in self.groups:
                # untimed line picked
                print self.groups['untimed'][event.artist._line_id].line_str
                return
            
            # only print loglines of visible points
            if not event.artist.get_visible():
                return

            indices = event.ind
            for i in indices:
                print self.groups[group][i].line_str

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
                # fast filtering for timed lines before creating logline objects
                if self.args['untimed'] or re.search(r'[0-9]ms$', line.rstrip()):
                    logline = LogLine(line)
                    if logline.namespace == None:
                        logline._namespace = "None"
                else:
                    continue

                if not (self.args['untimed'] or logline.duration):
                    continue

                if self.args['ns'] == None or logline.namespace in self.args['ns']:
                    if self.args['exclude_ns'] == None or (not logline.namespace in self.args['exclude_ns']):
                        if logline.datetime != None:
                            self.loglines.append(logline)

        # close files after parsing
        if sys.stdin.isatty():
            for f in logfiles:
                f.close()


    def _save_overlay(self):
        # make directory if not present
        group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(group_path):
            try:
                os.makedirs(group_path)
            except OSError:
                SystemExit("Couldn't create directory %s, quitting. Check permissions, or run without --overlay to display directly." % group_path)

        # create unique filename
        while True:
            uid = str(uuid.uuid4())[:8]
            group_file = os.path.join(group_path, uid)
            if not os.path.exists(group_file):
                break

        # dump groups and handle exceptions
        try:
            cPickle.dump(self.groups, open(group_file, 'wb'), -1)
            print "Created overlay: %s" % uid
        except Exception as e:
            print "Error: %s" % e
            SystemExit("Couldn't write to %s, quitting. Check permissions, or run without --overlay to display directly." % group_file)


    def _load_overlays(self):
        group_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(group_path):
            return False

        # load groups and merge
        group_files = glob.glob(os.path.join(group_path, '*'))
        for f in group_files:
            try:
                group_dict = cPickle.load(open(f, 'rb'))
            except Exception as e:
                print "Couldn't read overlay %s, skipping." % f
                continue

            # extend each list according to its key
            for key in group_dict:
                self.groups.setdefault(key, list()).extend(group_dict[key])
            
            print "Loaded overlay: %s" % os.path.basename(f)
        
        if len(group_files) > 0:
            print

        return len(group_files) > 0


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


    def _group_untimed(self):

        self.groups = OrderedDict()
        for i, logline in enumerate(self.loglines):
            key = "untimed"
            self.groups.setdefault(key, list()).append(self.loglines[i])

        del self.loglines


    def _group(self, group_by):
        if not group_by in ['namespace', 'operation', 'thread']:
            return

        self.groups = OrderedDict()
        for i, logline in enumerate(self.loglines):
            key = getattr(logline, group_by)
            
            # convert None to string
            if key == None:
                key = "None"

            # special case: group together all connections
            if group_by == "thread" and key.startswith("conn"):
                key = "conn####"

            self.groups.setdefault(key, list()).append(self.loglines[i])

        del self.loglines


    def _print_shortcuts(self):
        print "keyboard shortcuts (focus must be on figure window):"
        print "%5s  %s" % ("1-9", "toggle visibility of individual plots 1-9")
        print "%5s  %s" % ("0", "toggle visibility of all plots")
        print "%5s  %s" % ("q", "quit mplotqueries")


    def _plot_group(self, group, idx):
        x = date2num( [logline.datetime for logline in self.groups[group]] )

        if group != "untimed":
            # timed plots require y coordinate and use plot_date
            y = [ logline.duration for logline in self.groups[group] ]
            artist = plt.plot_date(x, y, color=self.colors[idx%len(self.colors)], \
                marker=self.markers[(idx / 7) % len(self.markers)], alpha=0.5, \
                markersize=7, picker=5, label=group)[0]

        else:
            # untimed plots plot with axvline
            for i, xcoord in enumerate(x):
                artist = plt.gca().axvline(xcoord, linewidth=1, picker=5, color=[0.8, 0.8, 0.8])
                artist._line_id = i

        return artist


    def plot(self):
        self.artists = []

        print "%3s %9s  %s"%("id", " #points", "group")
        
        # plot untimed first if present
        if "untimed" in self.groups:
            self.artists.append( self._plot_group("untimed", 0) )
 
        # then plot all other groups
        for idx, group in enumerate([g for g in self.groups if g != "untimed"]):
            print "%3s %9s  %s"%(idx+1, len(self.groups[group]), group)
            self.artists.append( self._plot_group(group, idx) )

        print
        
        self._print_shortcuts()

        plt.xlabel('time')
        plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))
        plt.xticks(rotation=90, fontsize=10)

        for label in plt.gca().get_xticklabels():  # make the xtick labels pickable
            label.set_picker(True)

        # log y axis
        if self.args['log']:
            plt.gca().set_yscale('log')
            plt.ylabel('query duration in ms (log scale)')
        else:
            plt.ylabel('query duration in ms')

        if not self.args['no_legend']:
            self.legend = plt.legend(loc='upper left', frameon=False, numpoints=1, fontsize=9)

        plt.gcf().canvas.mpl_connect('pick_event', self._onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self._onpress)

        plt.show()


if __name__ == '__main__':
    mplotqueries = MongoPlotQueries()

