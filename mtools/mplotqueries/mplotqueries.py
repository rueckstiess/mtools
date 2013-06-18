#!/usr/bin/python

import argparse
import re
import os
import sys
import uuid
import glob
import cPickle
import types
from copy import copy

try:
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter
    from matplotlib.lines import Line2D
    from matplotlib.text import Text
    from mtools.mplotqueries.plottypes import DurationPlotType, EventPlotType, RangePlotType, RSStatePlotType
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")


from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool

class MPlotQueriesTool(LogFileTool):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        self.argparser.description='A script to plot various information from logfiles. ' \
            'Clicking on any of the plot points will print the corresponding log line to stdout.'

        self.plot_types = [DurationPlotType, EventPlotType, RangePlotType, RSStatePlotType]
        self.plot_types = dict((pt.plot_type_str, pt) for pt in self.plot_types)
        self.plot_instances = []

        # main parser arguments
        self.argparser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')
        self.argparser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
        self.argparser.add_argument('--logscale', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        self.argparser.add_argument('--overlay', action='store', nargs='?', default=None, const='add', choices=['add', 'list', 'reset'])
        self.argparser.add_argument('--type', action='store', default='duration', choices=self.plot_types.keys(), help='type of plot (default=duration)')
        
        mutex = self.argparser.add_mutually_exclusive_group()
        mutex.add_argument('--group', help="specify value to group on. Possible values depend on type of plot. All basic plot types can group on 'namespace', 'operation', 'thread', range plots can additionally group on 'log2code'.")
        mutex.add_argument('--label', help="instead of specifying a group, a label can be specified. Grouping is then disabled, and the single group for all data points is named LABEL.")

        self.legend = None

    def run(self):
        LogFileTool.run(self)

        self.parse_loglines()
        self.group()

        if self.args['overlay'] == 'reset':
            self.remove_overlays()

        # if --overlay is set, save groups in a file, else load groups and plot
        if self.args['overlay'] == "list":
            self.list_overlays()
            raise SystemExit
        elif self.args['overlay'] == "" or self.args['overlay'] == "add":
            self.save_overlay()
            raise SystemExit

        plot_specified = not sys.stdin.isatty() or len(self.args['logfile']) > 0

        # if no plot is specified (either pipe or filename(s)) and reset, quit now
        if not plot_specified and self.args['overlay'] == 'reset':
            raise SystemExit

        # else plot (with potential overlays) if there is something to plot
        overlay_loaded = self.load_overlays()
        if plot_specified or overlay_loaded:
            self.plot()
        else:
            print "Nothing to plot."
            raise SystemExit


    def parse_loglines(self):
        multiple_files = False

        # create generator for logfile(s) handles
        if type(self.args['logfile']) != types.ListType:
            logfiles = [self.args['logfile']]
        else:
            logfiles = self.args['logfile']
            
        if len(logfiles) > 1:
            multiple_files = True
            self.args['group'] = 'filename'
        
        plot_instance = self.plot_types[self.args['type']](args=self.args)
        
        for logfile in logfiles:

            for line in logfile:
                # create LogLine object
                logline = LogLine(line)

                if multiple_files:
                    # amend logline object with filename for group by filename
                    logline.filename = logfile.name

                # offer plot_instance and see if it can plot it
                line_accepted = False
                if plot_instance.accept_line(logline):
                    
                    # only add if it doesn't conflict with namespace restrictions
                    if self.args['ns'] != None and logline.namespace not in self.args['ns']:
                        continue

                    if self.args['exclude_ns'] != None and (logline.namespace in self.args['exclude_ns']):
                        continue

                    # if logline doesn't have datetime, skip
                    if logline.datetime == None:
                        continue
                    
                    if logline.namespace == None:
                        logline._namespace = "None"

                    line_accepted = True
                    plot_instance.add_line(logline)

        self.plot_instances.append(plot_instance)

        # close files after parsing
        if sys.stdin.isatty():
            for f in logfiles:
                f.close()


    def group(self):
        self.plot_instances = [pi for pi in self.plot_instances if not pi.empty]
        for plot_inst in self.plot_instances:
            plot_inst.group()

    
    def list_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path, self.overlay_path)
        if not os.path.exists(target_path):
            return

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        print "Existing overlays:"
        for f in target_files:
            print "  ", os.path.basename(f)


    def save_overlay(self):
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


    def load_overlays(self):
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


    def remove_overlays(self):
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


    def print_shortcuts(self):
        print "keyboard shortcuts (focus must be on figure window):"
        print "%5s  %s" % ("1-9", "toggle visibility of individual plots 1-9")
        print "%5s  %s" % ("0", "toggle visibility of all plots")
        print "%5s  %s" % ("-", "toggle visibility of legend")
        print "%5s  %s" % ("g", "toggle grid")
        print "%5s  %s" % ("l", "toggle log/linear y-axis")
        print "%5s  %s" % ("q", "quit mplotqueries")
        print


    def onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """        
        # only print loglines of visible points
        if not event.artist.get_visible():
            return

        # get PlotType and let it print that event
        plot_type = event.artist._mt_plot_type
        plot_type.print_line(event)


    def toggle_artist(self, artist):
        try:
            visible = artist.get_visible()
            artist.set_visible(not visible)
            plt.gcf().canvas.draw()
        except Exception:
            pass


    def onpress(self, event):
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key)-1
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass

        if event.key == '0':
            visible = any([a.get_visible() for a in self.artists])
            for artist in self.artists:
                artist.set_visible(not visible)
            plt.gcf().canvas.draw()

        if event.key == 'q':
            raise SystemExit('quitting.')

        if event.key == '-':
            if self.legend:
                self.toggle_artist(self.legend)
                plt.gcf().canvas.draw()


    def plot(self):
        self.artists = []
        axis = plt.subplot(111)

        for i, plot_inst in enumerate(sorted(self.plot_instances, key=lambda pi: pi.sort_order)):
            self.artists.extend(plot_inst.plot(axis, i))
            
        self.print_shortcuts()

        axis.set_xlabel('time')
        axis.set_xticklabels(axis.get_xticks(), rotation=90, fontsize=10)
        axis.xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))

        for label in axis.get_xticklabels():  # make the xtick labels pickable
            label.set_picker(True)

        # log y axis
        if self.args['logscale']:
            axis.set_yscale('log')
            axis.set_ylabel('query duration in ms (log scale)')
        else:
            axis.set_ylabel('query duration in ms')

        handles, labels = axis.get_legend_handles_labels()
        if len(labels) > 0:
            self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1, fontsize=9)

        plt.gcf().canvas.mpl_connect('pick_event', self.onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self.onpress)

        plt.show()


if __name__ == '__main__':
    tool = MPlotQueriesTool()
    tool.run()


