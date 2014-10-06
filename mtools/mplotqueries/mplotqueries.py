#!/usr/bin/env python

import argparse
import re
import os
import sys
import uuid
import glob
import cPickle
import types
import inspect

from copy import copy
from mtools import __version__
from datetime import timedelta
from dateutil.tz import tzutc, tzoffset

try:
    import matplotlib.pyplot as plt
    from matplotlib.dates import AutoDateFormatter, date2num, AutoDateLocator
    from matplotlib.lines import Line2D
    from matplotlib.text import Text
    from matplotlib import __version__ as mpl_version
    import mtools.mplotqueries.plottypes as plottypes
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries that visualizes the logfile in a web browser.")


from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile

from mtools.util.cmdlinetool import LogFileTool

class MPlotQueriesTool(LogFileTool):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        self.argparser.description='A script to plot various information from logfiles. ' \
            'Clicking on any of the plot points will print the corresponding log line to stdout.'

        # disable some default shortcuts
        plt.rcParams['keymap.xscale'] = ''
        plt.rcParams['keymap.yscale'] = ''

        # import all plot type classes in plottypes module
        self.plot_types = [c[1] for c in inspect.getmembers(plottypes, inspect.isclass)]
        self.plot_types = dict((pt.plot_type_str, pt) for pt in self.plot_types)
        self.plot_instances = []

        # main parser arguments
        self.argparser.add_argument('--logscale', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        self.argparser.add_argument('--overlay', action='store', nargs='?', default=None, const='add', choices=['add', 'list', 'reset'], help="create combinations of several plots. Use '--overlay' to create an overlay (this will not plot anything). The first call without '--overlay' will additionally plot all existing overlays. Use '--overlay reset' to clear all overlays.")
        self.argparser.add_argument('--type', action='store', default='scatter', choices=self.plot_types.keys(), help='type of plot (default=scatter with --yaxis duration).')        
        self.argparser.add_argument('--title', action='store', default=None, help='change the title of the plot (default=filename(s))')        
        self.argparser.add_argument('--group', help="specify value to group on. Possible values depend on type of plot. All basic plot types can group on 'namespace', 'operation', 'thread', 'pattern', range and histogram plots can additionally group on 'log2code'. The group can also be a regular expression.")
        self.argparser.add_argument('--group-limit', metavar='N', type=int, default=None, help="specify an upper limit of the number of groups. Groups are sorted by number of data points. If limit is specified, only the top N will be listed separately, the rest are grouped together in an 'others' group")
        self.argparser.add_argument('--no-others', action='store_true', default=False, help="if this flag is used, the 'others' group (see --group-limit) will be discarded.")
        self.argparser.add_argument('--optime-start', action='store_true', default=False, help="plot operations with a duration when they started instead (by subtracting the duration). The default is to plot them when they finish (at the time they are logged).")
        self.argparser.add_argument('--ylimits', action='store', default=None, type=int, nargs=2, metavar='VAL', help="if set, limits the y-axis view to [min, max], requires exactly 2 values.")
        self.legend = None

        # progress bar
        self.progress_bar_enabled = not self.is_stdin


    def run(self, arguments=None):
        LogFileTool.run(self, arguments, get_unknowns=True)

        self.parse_logevents()
        self.group()

        if self.args['overlay'] == 'reset':
            self.remove_overlays()

        # if --overlay is set, save groups in a file, else load groups and plot
        if self.args['overlay'] == "list":
            self.list_overlays()
            raise SystemExit

        plot_specified = not sys.stdin.isatty() or len(self.args['logfile']) > 0

        # if no plot is specified (either pipe or filename(s)) and reset, quit now
        if not plot_specified and self.args['overlay'] == 'reset':
            raise SystemExit
        
        if self.args['overlay'] == "" or self.args['overlay'] == "add":
            if plot_specified:
                self.save_overlay()
            else:
                print "Nothing to plot."
            raise SystemExit

        # else plot (with potential overlays) if there is something to plot
        overlay_loaded = self.load_overlays()
        
        if plot_specified or overlay_loaded:
            self.plot()
        else:
            print "Nothing to plot."
            raise SystemExit


    def parse_logevents(self):
        multiple_files = False

        # create generator for logfile(s) handles
        if type(self.args['logfile']) != types.ListType:
            self.logfiles = [self.args['logfile']]
        else:
            self.logfiles = self.args['logfile']
            
        if len(self.logfiles) > 1:
            # force "logfile" to be the group key for multiple files
            multiple_files = True
            self.args['group'] = 'filename'
        
        plot_instance = self.plot_types[self.args['type']](args=self.args, unknown_args=self.unknown_args)

        for logfile in self.logfiles:
            
            # get log file information
            if self.progress_bar_enabled:
                if logfile.start and logfile.end:
                    progress_start = self._datetime_to_epoch(logfile.start)
                    progress_total = self._datetime_to_epoch(logfile.end) - progress_start
                else:
                    self.progress_bar_enabled = False
                
                if progress_total == 0:
                    # protect from division by zero errors
                    self.progress_bar_enabled = False

            for i, logevent in enumerate(logfile):

                # adjust times if --optime-start is enabled
                if self.args['optime_start'] and logevent.duration != None and logevent.datetime:
                    # create new variable end_datetime in logevent object and store starttime there
                    logevent.end_datetime = logevent.datetime 
                    logevent._datetime = logevent._datetime - timedelta(milliseconds=logevent.duration)
                    logevent._datetime_calculated = True

                # update progress bar every 1000 lines
                if self.progress_bar_enabled and (i % 1000 == 0) and logevent.datetime:
                    progress_curr = self._datetime_to_epoch(logevent.datetime)
                    self.update_progress(float(progress_curr-progress_start) / progress_total, 'parsing %s'%logfile.name)

                # offer plot_instance and see if it can plot it
                if plot_instance.accept_line(logevent):
                    
                    # if logevent doesn't have datetime, skip
                    if logevent.datetime == None:
                        continue
                    
                    if logevent.namespace == None:
                        logevent._namespace = "None"

                    plot_instance.add_line(logevent)

                if multiple_files:
                    # amend logevent object with filename for group by filename
                    logevent.filename = logfile.name


            # store start and end for each logfile (also works for system.profile and stdin stream)
            plot_instance.date_range = (logfile.start, logfile.end)

        # clear progress bar
        if self.logfiles and self.progress_bar_enabled:
            self.update_progress(1.0)

        self.plot_instances.append(plot_instance)


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
        print "\nkeyboard shortcuts (focus must be on figure window):\n"

        print "    %8s  %s" % ("p", "switch to pan mode")
        print "    %8s  %s" % ("o", "switch to zoom mode")
        print "    %8s  %s" % ("left/right", "back / forward")
        print "    %8s  %s" % ("h", "home (original view)")
        print "    %8s  %s" % ("l", "toggle log/linear y-axis")
        print "    %8s  %s" % ("f", "toggle fullscreen")
        print "    %8s  %s" % ("1-9", "toggle visibility of top 10 individual plots 1-9")
        print "    %8s  %s" % ("0", "toggle visibility of all plots")
        print "    %8s  %s" % ("-", "toggle visibility of legend")
        print "    %8s  %s" % ("g", "toggle grid")
        print "    %8s  %s" % ("c", "toggle 'created with' footnote")
        print "    %8s  %s" % ("s", "save figure")
        print "    %8s  %s" % ("q", "quit mplotqueries")

        print


    def onpick(self, event):
        """ this method is called per artist (group), with possibly
            a list of indices.
        """   
        if hasattr(event.artist, '_mt_legend_item'):
            # legend item, instead of data point
            idx = event.artist._mt_legend_item
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass
            return

        # only print logevents of visible points
        if not event.artist.get_visible():
            return

        # get PlotType and let it print that event
        plot_type = event.artist._mt_plot_type
        plot_type.clicked(event)


    def toggle_artist(self, artist):
        try:
            visible = artist.get_visible()
            artist.set_visible(not visible)
            plt.gcf().canvas.draw()
        except Exception:
            pass


    def onpress(self, event):
        # number keys
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key)-1
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass

        # 0, toggle all plots
        if event.key == '0':
            try:
                visible = any([a.get_visible() for a in self.artists])
            except AttributeError:
                return

            for artist in self.artists:
                artist.set_visible(not visible)
            plt.gcf().canvas.draw()

        # quit
        if event.key == 'q':
            raise SystemExit('quitting.')

        # toggle legend
        if event.key == '-':
            if self.legend:
                self.toggle_artist(self.legend)
                plt.gcf().canvas.draw()

        # toggle created footnote
        if event.key == 'c':
            self.toggle_artist(self.footnote)
            plt.gcf().canvas.draw()

        # toggle yaxis logscale
        if event.key == 'l':
            scale = plt.gca().get_yscale()
            if scale == 'linear':
                plt.gca().set_yscale('log')
            else:
                plt.gca().set_yscale('linear')

            plt.autoscale(True, axis='y', tight=True)
            # honor forced limits
            if self.args['ylimits']:
                plt.gca().set_ylim( self.args['ylimits'] )

            plt.gcf().canvas.draw()


    def plot(self):
        # check if there is anything to plot
        if len(self.plot_instances) == 0:
            raise SystemExit('no data to plot.')

        self.artists = []
        plt.figure(figsize=(12,8), dpi=100, facecolor='w', edgecolor='w')
        axis = plt.subplot(111)

        # set xlim from min to max of logfile ranges
        xlim_min = min([pi.date_range[0] for pi in self.plot_instances])
        xlim_max = max([pi.date_range[1] for pi in self.plot_instances])

        if xlim_max < xlim_min:
            raise SystemExit('no data to plot.')

        xlabel = 'time'
        ylabel = ''

        # use timezone of first log file (may not always be what user wants but must make a choice)
        tz = self.args['logfile'][0].timezone
        tzformat = '%b %d\n%H:%M:%S' if tz == tzutc() else '%b %d\n%H:%M:%S%z'

        locator = AutoDateLocator(tz=tz, minticks=5, maxticks=10)
        formatter = AutoDateFormatter(locator, tz=tz)

        formatter.scaled = {
           365.0  : '%Y',
           30.    : '%b %Y',
           1.0    : '%b %d %Y',
           1./24. : '%b %d %Y\n%H:%M:%S',
           1./(24.*60.): '%b %d %Y\n%H:%M:%S',
        }

        # add timezone to format if not UTC
        if tz != tzutc():
            formatter.scaled[1./24.] = '%b %d %Y\n%H:%M:%S%z'
            formatter.scaled[1./(24.*60.)] = '%b %d %Y\n%H:%M:%S%z'

        for i, plot_inst in enumerate(sorted(self.plot_instances, key=lambda pi: pi.sort_order)):
            self.artists.extend(plot_inst.plot(axis, i, len(self.plot_instances), (xlim_min, xlim_max) ))
            if hasattr(plot_inst, 'xlabel'):
                xlabel = plot_inst.xlabel
            if hasattr(plot_inst, 'ylabel'):
                ylabel = plot_inst.ylabel
        self.print_shortcuts()

        axis.set_xlabel(xlabel)
        axis.set_xticklabels(axis.get_xticks(), rotation=90, fontsize=9)
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(formatter)
            
        axis.set_xlim(date2num([xlim_min, xlim_max]))

        # ylabel for y axis
        if self.args['logscale']:
            ylabel += ' (log scale)'
        axis.set_ylabel(ylabel)

        # title and mtools link
        axis.set_title(self.args['title'] or ', '.join([l.name for l in self.logfiles if l.name != '<stdin>']))
        plt.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.95)
        self.footnote = plt.annotate('created with mtools v%s: https://github.com/rueckstiess/mtools' % __version__, (10, 10), xycoords='figure pixels', va='bottom', fontsize=8)

        handles, labels = axis.get_legend_handles_labels()
        if len(labels) > 0:
            # only change fontsize if supported 
            major, minor, _ = mpl_version.split('.')
            if (int(major), int(minor)) >= (1, 3):
                self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1, fontsize=9)
            else:
                self.legend = axis.legend(loc='upper left', frameon=False, numpoints=1)
        
        if self.args['type'] == 'scatter':
            # enable legend picking for scatter plots
            for i, legend_line in enumerate(self.legend.get_lines()):
                legend_line.set_picker(10)
                legend_line._mt_legend_item = i

        # overwrite y-axis limits if set
        if self.args['ylimits'] != None:
            print self.args['ylimits']
            axis.set_ylim( self.args['ylimits'])

        plt.gcf().canvas.mpl_connect('pick_event', self.onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self.onpress)
        plt.show()

if __name__ == '__main__':
    tool = MPlotQueriesTool()
    tool.run()


