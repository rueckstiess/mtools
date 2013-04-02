#!/usr/bin/python

import argparse
import re
import sys
import matplotlib.pyplot as plt

from mtools.mtoolbox.logline import LogLine
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.dates import date2num, DateFormatter
from collections import OrderedDict


class MongoPlotQueries(object):

    def __init__(self):
        self.colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        self.markers = ['o', 's', '<', 'D']
        self.loglines = []
        self.parseArgs()

        self._parse_loglines()
        self._group(self.args['group'])

        self.plot()


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
        parser.add_argument('--no-legend', action='store_true', default=False, help='turn off legend (default=on)')
        parser.add_argument('--group', action='store', default='namespace', choices=['namespace', 'operation', 'thread'], 
            help="group by namespace (default), operation or thread.")

        self.args = vars(parser.parse_args())
        # print self.args


    def _onpick(self, event):
        if isinstance(event.artist, Line2D):
            group = event.artist.get_label()
            indices = event.ind
            for i in indices:
                print self.loglines[self.groups[group][i]].line_str

        elif isinstance(event.artist, Text):
            text = event.artist
            # output mlogfilter output
            time_str = text.get_text().replace('\n', ' ')
            file_name = self.args['filename'] if 'filename' in self.args else ''
            print "mlogfilter %s --from %s"%(file_name, time_str)


    def _onpress(self, event):
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key)-1
            try:
                visible = self.artists[idx].get_visible()
                self.artists[idx].set_visible(not visible)
                plt.gcf().canvas.draw()
            except IndexError:
                pass

        if event.key == '0':

            visible = any([a.get_visible() for a in self.artists])
            for artist in self.artists:
                artist.set_visible(not visible)
            
            plt.gcf().canvas.draw()


    def _parse_loglines(self):
        # open logfile
        if sys.stdin.isatty():
            logfile = open(self.args['filename'], 'r')
        else:
            logfile = sys.stdin

        for line in logfile:
            # fast filtering for timed lines before creating logline objects
            if re.search(r'[0-9]ms$', line.rstrip()):
                logline = LogLine(line)
                if logline.namespace == None:
                    logline._namespace = "None"
            else:
                continue

            if not logline.duration:
                continue

            if self.args['ns'] == None or logline.namespace in self.args['ns']:
                if self.args['exclude_ns'] == None or (not logline.namespace in self.args['exclude_ns']):
                    if logline.datetime != None:
                        self.loglines.append(logline)


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

            self.groups.setdefault(key, list()).append(i)


    def plot(self):
        group_keys = self.groups.keys()
        self.artists = []

        print "%3s %9s  %s"%("id", " #points", "group")
        for idx,key in enumerate(group_keys):
            print "%3s %9s  %s"%(idx+1, len(self.groups[key]), key)

            x = date2num( [self.loglines[i].datetime for i in self.groups[key]] )
            y = [ self.loglines[i].duration for i in self.groups[key] ]

            self.artists.append( plt.plot_date(x, y, color=self.colors[idx%len(self.colors)], \
                marker=self.markers[(idx / 7) % len(self.markers)], alpha=0.5, \
                markersize=7, picker=5, label=key)[0] )
        print

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

"""
mplotqueries LOGFILE [-ns COLL COLL ...]

"""
