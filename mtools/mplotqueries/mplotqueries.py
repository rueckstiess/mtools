#!/usr/bin/env python3

import inspect
import os
import sys
from datetime import timedelta

from dateutil.tz import tzutc

from mtools import __version__
from mtools.mplotqueries.overlays import OverlayMixin
from mtools.util.cmdlinetool import LogFileTool

try:
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.dates import AutoDateFormatter, date2num, AutoDateLocator
    import mtools.mplotqueries.plottypes as plottypes
    from mtools.mplotqueries.plottypes.base_type import (BasePlotType,
                                                         PALETTES)
    import re

except ImportError as e:
    raise ImportError(f"Can't import matplotlib: {str(e)}\n\n"
                       "For installation instructions, see:\n"
                       "   https://matplotlib.org/stable/users/installing/index.html")


def op_or_cmd(le):
    return le.operation if le.operation != 'command' else le.command


class MPlotQueriesTool(OverlayMixin, LogFileTool):

    home_path = os.path.expanduser("~")
    mtools_path = '.mtools'
    overlay_path = 'mplotqueries/overlays/'

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        self.argparser.description = ("A script to plot various information "
                                      "from logfiles. Clicking on any of the "
                                      "plot points will print the "
                                      "corresponding log line to stdout.")

        # disable some default shortcuts
        plt.rcParams['keymap.xscale'] = ''
        plt.rcParams['keymap.yscale'] = ''

        # import all plot type classes in plottypes module
        self.plot_types = [c[1] for c in inspect.getmembers(plottypes,
                                                            inspect.isclass)]
        self.plot_types = dict((pt.plot_type_str,
                                pt) for pt in self.plot_types)
        self.plot_instances = []
        self.plot_instance = None

        # main parser arguments
        self.argparser.add_argument('--logscale', action='store_true',
                                    help=('plot y-axis in logarithmic scale '
                                          '(default=off)'))
        self.argparser.add_argument('--overlay', action='store', nargs='?',
                                    default=None, const='add',
                                    choices=['add', 'list', 'reset'],
                                    help=("create combinations of several "
                                          "plots. Use '--overlay' to create "
                                          "an overlay (this will not plot "
                                          "anything). The first call without "
                                          "'--overlay' will additionally plot "
                                          "all existing overlays. Use "
                                          "'--overlay reset' to clear all "
                                          "overlays."))
        self.argparser.add_argument('--palette', action='store',
                                    default='default',
                                    choices=sorted(PALETTES),
                                    help=('color sequence for grouped plots. '
                                          'okabe-ito, tol, and ibm stay '
                                          'distinguishable for common kinds '
                                          'of color blindness. rsstate and '
                                          'connchurn keep their fixed state '
                                          'colors.'))
        self.argparser.add_argument('--colors', action='store', nargs='+',
                                    metavar='COLOR', default=None,
                                    help=('use these colors instead of '
                                          '--palette. Each value is #RGB, '
                                          '#RRGGBB, or a matplotlib color '
                                          'name.'))
        self.argparser.add_argument('--type', action='store',
                                    default='scatter',
                                    choices=self.plot_types.keys(),
                                    help=("type of plot (default=scatter with "
                                          "--yaxis duration)."))
        self.argparser.add_argument('--title', action='store', default=None,
                                    help=("change the title of the plot "
                                          "(default=filename(s))"))
        self.argparser.add_argument('--group',
                                    help=("specify value to group on. "
                                          "Possible values depend on type of "
                                          "plot. All basic plot types can "
                                          "group on 'namespace','hostname' 'operation', "
                                          "'thread', 'pattern'. The group can "
                                          "also be a regular expression."))
        self.argparser.add_argument('--group-limit', metavar='N', type=int,
                                    default=None,
                                    help=("specify an upper limit of the "
                                          "number of groups. Groups are "
                                          "sorted by number of data points. "
                                          "If limit is specified, only the "
                                          "top N will be listed separately, "
                                          "the rest are grouped together in "
                                          "an 'others' group"))
        self.argparser.add_argument('--no-others', action='store_true',
                                    default=False,
                                    help=("if this flag is used, the 'others' "
                                          "group (see --group-limit) will be "
                                          "discarded."))
        self.argparser.add_argument('--optime-start', action='store_true',
                                    default=False,
                                    help=("plot operations with a duration "
                                          "when they started instead (by "
                                          "subtracting the duration). The "
                                          "default is to plot them when they "
                                          "finish (at the time they are "
                                          "logged)."))
        self.argparser.add_argument('--ylimits', action='store', default=None,
                                    type=int, nargs=2, metavar='VAL',
                                    help=("if set, limits the y-axis view to "
                                          "[min, max], requires exactly 2 "
                                          "values."))
        self.argparser.add_argument('--output-file', metavar='FILE',
                                    action='store', default=None,
                                    help=("Save the plot to a file instead of "
                                          "displaying it in a window"))
        self.argparser.add_argument('--checkpoints',
                                    action='store_true', default=None,
                                    help=("plot slow WiredTiger checkpoints"))
        self.argparser.add_argument('--dns', action='store_true',
                                    help='plot slow DNS resolution', default=False)
        self.argparser.add_argument('--oplog', action='store_true',
                                    help=('plot slow oplog application'))

        self.legend = None
        self._legend_entries = []
        self._updating_legend = False

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

        plot_specified = (not sys.stdin.isatty() or
                          len(self.args['logfile']) > 0)

        # if no plot is specified (either pipe or filename(s)) and reset,
        # quit now
        if not plot_specified and self.args['overlay'] == 'reset':
            raise SystemExit

        if self.args['overlay'] == "" or self.args['overlay'] == "add":
            if plot_specified:
                self.save_overlay()
            else:
                print("Nothing to plot.")
            raise SystemExit

        # else plot (with potential overlays) if there is something to plot
        overlay_loaded = self.load_overlays()

        if plot_specified or overlay_loaded:
            self.plot()
        else:
            print("Nothing to plot.")
            raise SystemExit

    def parse_logevents(self):
        multiple_files = False

        # create generator for logfile(s) handles
        if not isinstance(self.args['logfile'], list):
            self.logfiles = [self.args['logfile']]
        else:
            self.logfiles = self.args['logfile']

        if len(self.logfiles) > 1:
            # force "logfile" to be the group key for multiple files
            multiple_files = True
            self.args['group'] = 'filename'

        self.plot_instance = self.plot_types[
            self.args['type']](
                args=self.args,
                unknown_args=self.unknown_args)

        for logfile in self.logfiles:

            # get log file information
            if self.progress_bar_enabled:
                if logfile.start and logfile.end:
                    progress_start = self._datetime_to_epoch(logfile.start)
                    progress_total = (self._datetime_to_epoch(logfile.end) -
                                      progress_start)
                else:
                    self.progress_bar_enabled = False
                    progress_start = 0
                    progress_total = 1

                if progress_total == 0:
                    # protect from division by zero errors
                    self.progress_bar_enabled = False

            for i, logevent in enumerate(logfile):
                if (self.args['dns'] and
                        not re.search("DNS resolution while connecting to", logevent.line_str)):
                    continue

                if (self.args['checkpoints'] and
                        not re.search("Checkpoint took", logevent.line_str)):
                    continue

                if (self.args['oplog'] and
                        (logevent.component != "REPL" or
                            not re.search("applied op:", logevent.line_str))):
                    continue

                # adjust times if --optime-start is enabled
                if (self.args['optime_start'] and
                        logevent.duration is not None and logevent.datetime):
                    # create new variable end_datetime in logevent object
                    # and store starttime there
                    logevent.end_datetime = logevent.datetime
                    logevent._datetime = (logevent._datetime -
                                          timedelta(milliseconds=logevent
                                                    .duration))
                    logevent._datetime_calculated = True

                # update progress bar every 1000 lines
                if (self.progress_bar_enabled and (i % 1000 == 0) and
                        logevent.datetime):
                    progress_curr = self._datetime_to_epoch(logevent.datetime)
                    self.update_progress(float(progress_curr -
                                               progress_start) /
                                         progress_total,
                                         'parsing %s' % logfile.name)

                # offer plot_instance and see if it can plot it
                if self.plot_instance.accept_line(logevent):

                    # if logevent doesn't have datetime, skip
                    if logevent.datetime is None:
                        continue

                    if logevent.namespace is None:
                        logevent._namespace = "None"

                    self.plot_instance.add_line(logevent)

                if multiple_files:
                    # amend logevent object with filename for group by filename
                    logevent.filename = logfile.name

            # store start and end for each logfile
            # (also works for system.profile and stdin stream)
            range_min = min(self.plot_instance.date_range[0], logfile.start)
            range_max = max(self.plot_instance.date_range[1], logfile.end)
            self.plot_instance.date_range = (range_min, range_max)

        # --optime-start (and --type durline) move an operation to the
        # moment it began. A long operation can begin before the first
        # logged timestamp, so the initial view has to include that time.
        # Scan the events once, after all logfiles are read.
        if self.args['optime_start']:
            range_min, range_max = self.plot_instance.date_range
            for logevent in self.plot_instance.logevents:
                started = logevent.datetime
                if started is not None and started < range_min:
                    range_min = started
                finished = getattr(logevent, 'end_datetime', None)
                if finished is not None and finished > range_max:
                    range_max = finished
            self.plot_instance.date_range = (range_min, range_max)

        # clear progress bar
        if self.logfiles and self.progress_bar_enabled:
            self.update_progress(1.0)

        self.plot_instances.append(self.plot_instance)

    def group(self):
        self.plot_instances = [pi for pi in self.plot_instances
                               if not pi.empty]
        for plot_inst in self.plot_instances:
            plot_inst.group()

    def print_shortcuts(self, scatter=False):
        print("\nkeyboard shortcuts (focus must be on figure window):\n")

        print("    %8s  %s" % ("p", "switch to pan mode"))
        print("    %8s  %s" % ("o", "switch to zoom mode"))
        print("    %8s  %s" % ("left/right", "back / forward"))
        print("    %8s  %s" % ("h", "home (original view)"))
        print("    %8s  %s" % ("l", "toggle log/linear y-axis"))
        print("    %8s  %s" % ("f", "toggle fullscreen"))
        print("    %8s  %s"
              % ("1-9", "toggle visibility of top 10 individual plots 1-9"))
        print("    %8s  %s" % ("0", "toggle visibility of all plots"))
        print("    %8s  %s" % ("-", "toggle visibility of legend"))
        if scatter:
            print("    %8s  %s"
                  % ("[/]", "decrease / increase opacity by 10%"))
            print("    %8s  %s" % ("{/}", "decrease / increase opacity by 1%"))
            print("    %8s  %s" % ("</>", "decrease / increase marker size"))
            print("    %8s  %s" % ("e", "toggle marker edges"))
        print("    %8s  %s" % ("g", "toggle grid"))
        print("    %8s  %s" % ("c", "toggle 'created with' footnote"))
        print("    %8s  %s" % ("s", "save figure"))
        print("    %8s  %s" % ("q", "quit mplotqueries"))

        print("")

    def onpick(self, event):
        """Called per artist (group), with possibly a list of indices."""
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

    def _init_opacities(self):
        for artist in self.artists:
            if not hasattr(artist, '_mt_opacity'):
                artist._mt_opacity = artist.get_alpha()

    def _any_opacities_to_increase(self):
        for artist in self.artists:
            if artist._mt_opacity < 0.99:
                return True
        return False

    def _any_opacities_to_decrease(self):
        for artist in self.artists:
            if artist._mt_opacity > 0.01:
                return True
        return False

    def set_opacities(self):
        for artist in self.artists:
            if artist._mt_opacity > 1.0:
                artist.set_alpha(1.0)
            elif artist._mt_opacity < 0.01:
                artist.set_alpha(0.01)
            else:
                artist.set_alpha(artist._mt_opacity)

    def increase_opacity(self, amount):
        self._init_opacities()
        if self._any_opacities_to_increase():
            for artist in self.artists:
                artist._mt_opacity = artist._mt_opacity + amount
            self.set_opacities()

    def decrease_opacity(self, amount):
        self._init_opacities()
        if self._any_opacities_to_decrease():
            for artist in self.artists:
                artist._mt_opacity = artist._mt_opacity - amount
            self.set_opacities()

    def toggle_marker_edges(self):
        for artist in self.artists:
            if artist.get_markeredgewidth() != 0:
                artist._mt_markeredgewidth = artist.get_markeredgewidth()
                artist.set_markeredgewidth(0)
            else:
                artist.set_markeredgewidth(artist._mt_markeredgewidth)

    def _init_markersizes(self):
        for artist in self.artists:
            if not hasattr(artist, '_mt_markersize'):
                artist._mt_markersize = artist.get_markersize()

    def _any_markersizes_to_increase(self):
        for artist in self.artists:
            if artist._mt_markersize < 10.0:
                return True
        return False

    def _any_markersizes_to_decrease(self):
        for artist in self.artists:
            if artist._mt_markersize > 1.0:
                return True
        return False

    def set_markersizes(self):
        for artist in self.artists:
            if artist._mt_markersize > 10.0:
                artist.set_markersize(10.0)
            elif artist._mt_markersize < 1.01:
                artist.set_markersize(1.0)
            else:
                artist.set_markersize(artist._mt_markersize)

    def increase_marker_size(self, amount=1):
        self._init_markersizes()
        if self._any_markersizes_to_increase():
            for artist in self.artists:
                artist._mt_markersize = artist._mt_markersize + amount
            self.set_markersizes()

    def decrease_marker_size(self, amount=1):
        self._init_markersizes()
        if self._any_markersizes_to_decrease():
            for artist in self.artists:
                artist._mt_markersize = artist._mt_markersize - amount
            self.set_markersizes()

    def onpress(self, event):
        # number keys
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key) - 1
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
                plt.gca().set_ylim(self.args['ylimits'])

            plt.gcf().canvas.draw()

        # opacity
        if isinstance(self.plot_instance, plottypes.ScatterPlotType):
            if event.key == '[':
                self.decrease_opacity(0.10)
                plt.gcf().canvas.draw()

            if event.key == '{':
                self.decrease_opacity(0.01)
                plt.gcf().canvas.draw()

            if event.key == ']':
                self.increase_opacity(0.10)
                plt.gcf().canvas.draw()

            if event.key == '}':
                self.increase_opacity(0.01)
                plt.gcf().canvas.draw()

            # edge on/off
            if event.key == 'e':
                self.toggle_marker_edges()
                plt.gcf().canvas.draw()

            # marker size
            if event.key == '<':
                self.decrease_marker_size()
                plt.gcf().canvas.draw()

            if event.key == '>':
                self.increase_marker_size()
                plt.gcf().canvas.draw()

    def _artist_points(self, artist):
        """Return ``(xs, ys)`` for an artist that stores point data."""
        get_x = getattr(artist, 'get_xdata', None)
        get_y = getattr(artist, 'get_ydata', None)
        if get_x is None or get_y is None:
            return None, None
        return list(get_x()), list(get_y())

    def _artist_in_view(self, artist, xmin, xmax, ymin, ymax):
        """Return True when this artist draws something inside the view."""
        patches = getattr(artist, 'patches', None)
        if patches is not None:
            # a bar container: in view when any bar overlaps the x-range
            return any(self._artist_in_view(patch, xmin, xmax, ymin, ymax)
                       for patch in patches)
        if hasattr(artist, 'get_width') and hasattr(artist, 'get_x'):
            # a bar: test its horizontal extent
            x0 = artist.get_x()
            x1 = x0 + artist.get_width()
            return min(x0, x1) <= xmax and max(x0, x1) >= xmin

        xs, ys = self._artist_points(artist)
        if xs is None:
            return True
        if len(xs) == 0:
            return False

        axes = getattr(artist, 'axes', None)
        if axes is not None and artist.get_transform() is not axes.transData:
            # axvline and friends put y in axes fraction; only x is data
            return any(x is not None and xmin <= x <= xmax for x in xs)

        linestyle = getattr(artist, 'get_linestyle', lambda: 'None')()
        draws_line = linestyle not in (None, 'None', 'none')
        if draws_line and len(xs) >= 2 and len(ys) >= 2:
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            spans_view = (x1 >= xmin and x0 <= xmax and
                          y1 >= ymin and y0 <= ymax)
            if spans_view:
                return True

        for x, y in zip(xs, ys):
            if x is None or y is None:
                continue
            if xmin <= x <= xmax and ymin <= y <= ymax:
                return True
        return False

    def _series_in_view(self, handle, xmin, xmax, ymin, ymax):
        """Return True when any artist in this series meets the view."""
        group = getattr(handle, '_mt_group', None)
        plot_type = getattr(handle, '_mt_plot_type', None)
        if group is None:
            related = [handle]
        else:
            related = [artist for artist in self.artists
                       if getattr(artist, '_mt_group', None) == group and
                       getattr(artist, '_mt_plot_type', None) is plot_type]
            if handle not in related:
                related.append(handle)
        # hidden series stay listed so they can be toggled back on
        return any(self._artist_in_view(artist, xmin, xmax, ymin, ymax)
                   for artist in related)

    def _refresh_legend(self, axis):
        """Rebuild the legend from groups that intersect the current view."""
        if self._updating_legend or not self._legend_entries:
            return
        xmin, xmax = axis.get_xlim()
        ymin, ymax = axis.get_ylim()
        shown = [(handle, label) for handle, label in self._legend_entries
                 if self._series_in_view(handle, xmin, xmax, ymin, ymax)]

        self._updating_legend = True
        legend_visible = True
        try:
            if self.legend is not None:
                legend_visible = self.legend.get_visible()
                self.legend.remove()
                self.legend = None
            if not shown:
                return
            handles = [handle for handle, _label in shown]
            labels = [label for _handle, label in shown]
            self.legend = axis.legend(handles, labels, loc='upper left',
                                      frameon=False, numpoints=1, fontsize=9)
            self.legend.set_visible(legend_visible)
            if self.args['type'] == 'scatter':
                index = dict((id(artist), i)
                             for i, artist in enumerate(self.artists))
                lines = self.legend.get_lines()
                for legend_line, handle in zip(lines, handles):
                    legend_line.set_picker(10)
                    legend_line._mt_legend_item = index.get(id(handle))
        finally:
            self._updating_legend = False

    def plot(self):
        # check if there is anything to plot
        if len(self.plot_instances) == 0:
            raise SystemExit('no data to plot.')

        BasePlotType.use_palette(self.args.get('palette') or 'default',
                                 self.args.get('colors'))

        if self.args['output_file'] is not None:
            # --output-file means don't depend on X,
            # so switch to a pure-image backend before doing any plotting.
            plt.switch_backend('agg')

        self.artists = []
        plt.figure(figsize=(12, 8), dpi=100, facecolor='w', edgecolor='w')
        axis = plt.subplot(111)

        # set xlim from min to max of logfile ranges
        xlim_min = min([pi.date_range[0] for pi in self.plot_instances])
        xlim_max = max([pi.date_range[1] for pi in self.plot_instances])

        if xlim_max < xlim_min:
            raise SystemExit('no data to plot.')

        xlabel = 'time'
        ylabel = ''

        # use timezone of first log file (may not always be what user wants
        # but must make a choice)
        tz = self.logfiles[0].timezone
        # tzformat='%b %d\n%H:%M:%S' if tz == tzutc() else '%b %d\n%H:%M:%S%z'

        locator = AutoDateLocator(tz=tz, minticks=5, maxticks=10)
        formatter = AutoDateFormatter(locator, tz=tz)

        formatter.scaled = {
            365.0: '%Y',
            30.: '%b %Y',
            1.0: '%b %d %Y',
            1. / 24.: '%b %d %Y\n%H:%M:%S',
            1. / (24. * 60.): '%b %d %Y\n%H:%M:%S',
            }

        # add timezone to format if not UTC
        if tz != tzutc():
            formatter.scaled[1. / 24.] = '%b %d %Y\n%H:%M:%S%z'
            formatter.scaled[1. / (24. * 60.)] = '%b %d %Y\n%H:%M:%S%z'

        for i, plot_inst in enumerate(sorted(self.plot_instances,
                                             key=lambda pi: pi.sort_order)):
            self.artists.extend(plot_inst.plot(axis, i,
                                               len(self.plot_instances),
                                               (xlim_min, xlim_max)))
            if hasattr(plot_inst, 'xlabel'):
                xlabel = plot_inst.xlabel
            if hasattr(plot_inst, 'ylabel'):
                ylabel = plot_inst.ylabel
        if self.args['output_file'] is None:
            self.print_shortcuts(scatter=isinstance(self.plot_instance,
                                                    plottypes.ScatterPlotType))

        axis.set_xlabel(xlabel)
        axis.set_xticklabels(axis.get_xticks(), rotation=90, fontsize=9)
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(formatter)

        axis.set_xlim(date2num([xlim_min, xlim_max]))

        # ylabel for y axis
        if self.args['logscale']:
            ylabel += ' (log scale)'
        axis.set_ylabel(ylabel)

        # enable grid
        axis.grid(True)

        # title and mtools link
        axis.set_title(self.args['title'] or
                       ', '.join([l.name for l in self.logfiles
                                  if l.name != '<stdin>']))
        plt.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.95)
        self.footnote = plt.annotate("created with mtools v%s: "
                                     "https://github.com/rueckstiess/mtools"
                                     % __version__, (10, 10),
                                     xycoords='figure pixels',
                                     va='bottom', fontsize=8)

        # overwrite y-axis limits if set, before the legend reads the view
        if self.args['ylimits'] is not None:
            print(self.args['ylimits'])
            axis.set_ylim(self.args['ylimits'])

        handles, labels = axis.get_legend_handles_labels()
        self._legend_entries = list(zip(handles, labels))
        # Zoom and pan change the view after the first draw. Keep the legend
        # to groups that still have a marker inside that view.
        axis.callbacks.connect('xlim_changed', self._refresh_legend)
        axis.callbacks.connect('ylim_changed', self._refresh_legend)
        self._refresh_legend(axis)

        plt.gcf().canvas.mpl_connect('pick_event', self.onpick)
        plt.gcf().canvas.mpl_connect('key_press_event', self.onpress)
        if self.args['output_file'] is not None:
            plt.savefig(self.args['output_file'])
        else:
            plt.show()


def main():
    tool = MPlotQueriesTool()
    tool.run()


if __name__ == '__main__':
    sys.exit(main())
