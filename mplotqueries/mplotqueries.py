#!/usr/bin/python

import datetime
import argparse
import re
import sys
import time
import matplotlib.pyplot as plt
import numpy as np

from mtools.mtoolbox.logline import LogLine
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.dates import date2num, DateFormatter
from collections import defaultdict


class MongoPlotQueries(object):

    def __init__(self):
        self.queries = []
        self.markers = ['o', 's', '<', 'D']
        self.loglines = defaultdict(list)
        self.parseArgs()

    def parseArgs(self):
        # create parser object
        parser = argparse.ArgumentParser(description='A script to plot query durations in a logfile' \
            ' (requires numpy and matplotlib packages). Clicking on any of the plot points will print' \
            ' the corresponding log line to stdout. Clicking on the x-axis labels will output an ' \
            ' "mlogfilter" string with the matching "--from" parameter.')
        
        parser.usage = "mplotqueries [-h] filename\n                    [--ns [NS [NS ...]]] [--log]\n                    [--exclude-ns [NS [NS ...]]]\n"

        # positional argument
        if sys.stdin.isatty():
            parser.add_argument('filename', action='store', help='logfile to parse')
        
        parser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
        parser.add_argument('--log', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        parser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')

        self.args = vars(parser.parse_args())
        # print self.args

    def _onpick(self, event):
        if isinstance(event.artist, Line2D):
            namespace = event.artist.get_label()
            ind = event.ind
            # print 'onpick line:', zip(np.take(xdata, ind), np.take(ydata, ind))
            for i in ind:
                print self.loglines[namespace][i].line_str

        elif isinstance(event.artist, Text):
            text = event.artist
            # output mlogfilter output
            time_str = text.get_text().replace('\n', ' ')
            file_name = self.args['filename'] if 'filename' in self.args else ''
            print "mlogfilter %s --from %s"%(file_name, time_str)

    def plot(self):
        durations = defaultdict(list)
        dates = defaultdict(list)

        # open logfile
        if sys.stdin.isatty():
            logfile = open(self.args['filename'], 'r')
        else:
            logfile = sys.stdin

        for line in logfile:
            if re.search(r'[0-9]ms$', line.rstrip()):
                logline = LogLine(line)
                if logline.namespace == None:
                    logline.namespace = "None"
            else:
                continue

            if not logline.duration:
                continue

            if self.args['ns'] == None or logline.namespace in self.args['ns']:
                if self.args['exclude_ns'] == None or (not logline.namespace in self.args['exclude_ns']):
                    if logline.datetime != None:
                        durations[logline.namespace].append(logline.duration)
                        dates[logline.namespace].append(logline.datetime)
                        self.loglines[logline.namespace].append(logline)

        for i,ns in enumerate(dates):
            print i, ns, len(dates[ns])
            d = date2num(dates[ns])
            plt.plot_date(d, durations[ns], self.markers[(i/7) % len(self.markers)], alpha=0.5, markersize=7, label=ns, picker=5)

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

        plt.legend(loc='upper left', frameon=False, fontsize=9)

        plt.gcf().canvas.mpl_connect('pick_event', self._onpick)
        plt.show()


if __name__ == '__main__':
    mplotqueries = MongoPlotQueries()
    mplotqueries.plot()

"""
mplotqueries LOGFILE [-ns COLL COLL ...]

"""