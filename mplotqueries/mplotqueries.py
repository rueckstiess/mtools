#!/usr/bin/python

import argparse
import re
import os
import sys
import uuid
import glob
import cPickle

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.lines import Line2D
from matplotlib.text import Text

from mtools.mtoolbox.logline import LogLine
from plottypes import DurationPlotType, EventPlotType, RangePlotType

class MongoPlotQueries(object):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        self.plot_types = {'duration': DurationPlotType, 'event': EventPlotType, 'range': RangePlotType}
        self.plot_instances = []

        # parse arguments
        self.parse_args()

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
        overlay_loaded = self._load_overlays()
        if plot_specified or overlay_loaded:
            self.plot()
        else:
            print "Nothing to plot."
            raise SystemExit


    def split_plot_args(self, args):
        """ iterator that splits ['--plot', 'a', '--group', 'b', '--plot', 'c', '--label', 'd']
            into separate lists [['a', '--group', 'b'], ['c', '--label', 'd']], removing all '--plot'
        """
        result = []
        for a in args:
            if a == "--plot":
                if len(result) > 0:
                    yield result
                    result = []
            else:
                result.append(a)
        yield result


    def parse_args(self):
        # create parser object
        parser = argparse.ArgumentParser(description='A script to plot query durations in a logfile' \
            ' (requires numpy and matplotlib packages). Clicking on any of the plot points will print' \
            ' the corresponding log line to stdout. Clicking on the x-axis labels will output an ' \
            ' "mlogfilter" string with the matching "--from" parameter.')
        
        parser.usage = "mplotqueries [-h] filename\n                    [--ns [NS [NS ...]]] [--log]\n                    [--exclude-ns [NS [NS ...]]]\n"

        # positional argument
        if sys.stdin.isatty():
            parser.add_argument('filename', action='store', nargs="*", help='logfile(s) to parse')
        
        # main parser arguments
        parser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')
        parser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
        parser.add_argument('--log', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        parser.add_argument('--no-legend', action='store_true', default=False, help='turn off legend (default=on)')
        parser.add_argument('--overlay', action='store', nargs='?', default=None, const='add', choices=['add', 'list', 'reset'])

        # separate parser for --plot arguments (multiple times possible)
        plotparser = argparse.ArgumentParser()
        plotparser.add_argument('type', choices=self.plot_types.keys())
        mutex = plotparser.add_mutually_exclusive_group()
        mutex.add_argument('--group')
        mutex.add_argument('--label')

        self.args, rest = parser.parse_known_args()
        self.args = vars(self.args)
        self.plot_args = [vars(plotparser.parse_args(r)) for r in self.split_plot_args(rest)]


    def _onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """        
        # only print loglines of visible points
        if not event.artist.get_visible():
            return

        # get PlotType and let it print that event
        plot_type = event.artist._mt_plot_type
        plot_type.print_line(event)

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
            plot_instances = []

            # create plot instances (one per --plot per file)
            for pa in self.plot_args:
                args = dict(self.args.items() + pa.items())

                # special case: for multiple files, set label to filename if undefined
                if len(self.args['filename']) > 1 and args['label'] == None:
                    args['label'] = logfile.name

                plot_instances.append( self.plot_types[pa['type']](args=args) )
                self.plot_instances.extend(plot_instances)

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
                for plot_inst in plot_instances:
                    if plot_inst.accept_line(logline):
                        line_accepted = True
                        plot_inst.add_line(logline)

        # close files after parsing
        if sys.stdin.isatty():
            for f in logfiles:
                f.close()


    def _group(self):
        self.plot_instances = [pi for pi in self.plot_instances if not pi.empty]
        for plot_inst in self.plot_instances:
            plot_inst.group_by()

    
    def _list_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        print "Existing overlays:"
        for f in target_files:
            print "  ", os.path.basename(f)


    def _save_overlay(self):
        # make directory if not present
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except OSError:
                SystemExit("Couldn't create directory %s, quitting. Check permissions, or run without --overlay to display directly." % overlay_path)

        # create unique filename
        while True:
            uid = str(uuid.uuid4())[:8]
            target_file = os.path.join(target_path, uid)
            if not os.path.exists(target_file):
                break

        # dump plots and handle exceptions
        try:
            cPickle.dump(self.plot_instances, open(target_file, 'wb'), -1)
            print "Created overlay: %s" % uid
        except Exception as e:
            print "Error: %s" % e
            SystemExit("Couldn't write to %s, quitting. Check permissions, or run without --overlay to display directly." % target_file)


    def _load_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return False

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        for f in target_files:
            try:
                overlay = cPickle.load(open(f, 'rb'))
            except Exception as e:
                print "Couldn't read overlay %s, skipping." % f
                continue

            # extend each list according to its key
            self.plot_instances.extend(overlay)
            # for key in group_dict:
            #     self.groups.setdefault(key, list()).extend(group_dict[key])
            
            print "Loaded overlay: %s" % os.path.basename(f)
        
        if len(target_files) > 0:
            print

        return len(target_files) > 0


    def _remove_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return 0

        target_files = glob.glob(os.path.join(target_path, '*'))
        # remove all group files
        for f in target_files:
            try:
                os.remove(f)
            except OSError as e:
                print "Error occured when deleting %s, skipping."
                continue

        if len(target_files) > 0:
            print "Deleted overlays."          


    def _print_shortcuts(self):
        print "keyboard shortcuts (focus must be on figure window):"
        print "%5s  %s" % ("1-9", "toggle visibility of individual plots 1-9")
        print "%5s  %s" % ("0", "toggle visibility of all plots")
        print "%5s  %s" % ("q", "quit mplotqueries")
        print


    def plot(self):
        self.artists = []
        axis = plt.subplot(111)

        for i, plot_inst in enumerate(sorted(self.plot_instances, key=lambda pi: pi.sort_order)):
            self.artists.extend(plot_inst.plot(axis, i))
            
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


