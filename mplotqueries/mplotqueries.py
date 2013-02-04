#!/usr/bin/python

import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter
import numpy as np
import argparse
import re
import sys
from mtools.mtoolbox.extractdate import extractDateTime
from collections import defaultdict


class Query(object):
    def __init__(self, querystr):
        self.qstr = querystr
        self._parse()

    def _parse(self):
        # extract date and time
        self.time = extractDateTime(self.qstr)
        
        items = self.qstr.split()
        if len(items) == 0:
            return None

        # extract duration
        self.duration = None
        if len(items) > 0 and items[-1].endswith('ms'):
            self.duration = int(items[-1][:-2])

        
        # extract connection
        self.connection = None
        for i in items:
            match = re.match(r'^\[(conn[^\]]*)\]$', i)
            if match:
                self.connection = match.group(1)
                break

        # extract namespace
        if '\x00query' in items:
            self.namespace = items[items.index('\x00query')+1]
        elif 'query' in items:
            self.namespace = items[items.index('query')+1]
        elif 'command' in items:
            self.namespace = '(command)'
        elif 'getmore' in items:
            self.namespace = '(getmore)'
        else:
            self.namespace = '(none)'

        # extract nscanned, ntoreturn, nreturned (if present)
        labels = ['nscanned', 'ntoreturn', 'nreturned']
        for i in items:
            for label in labels:
                if i.startswith('%s:'%label):
                    vars(self)[label] = i.split(':')[-1]
                    break


    def __str__(self):
        output = ''
        labels = ['time', 'connection', 'namespace', 'nscanned', 'ntoreturn', 'nreturned', 'duration']
        variables = vars(self)

        for label in labels:
            if not label in variables:
                continue
            output += '%s:'%label
            output += str(vars(self)[label])
            output += " "
        return output


class MongoPlotQueries(object):

    def __init__(self):
        self.queries = []
        self.markers = ['o', 's', '<', 'D']
        self.parseArgs()

    def parseArgs(self):
        # create parser object
        parser = argparse.ArgumentParser(description='script to plot query times from a logfile')
        
        # positional argument
        if sys.stdin.isatty():
            parser.add_argument('filename', action='store', help='logfile to parse')
        
        parser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
        parser.add_argument('--log', action='store_true', help='plot y-axis in logarithmic scale (default=off)')
        parser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')

        self.args = vars(parser.parse_args())
        print self.args


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
                query = Query(line)
            else:
                continue

            if not query:
                continue

            if self.args['ns'] == None or query.namespace in self.args['ns']:
                if self.args['exclude_ns'] == None or (not query.namespace in self.args['exclude_ns']):
                    if query.time != None:
                        durations[query.namespace].append(query.duration)
                        dates[query.namespace].append(query.time)

        for i,ns in enumerate(dates):
            print i, ns, len(dates[ns])
            durations_arr = np.array(durations[ns])

            d = date2num(dates[ns])
            plt.plot_date(d, durations_arr, self.markers[(i/7) % len(self.markers)], alpha=0.5, markersize=7, label=ns)

        plt.xlabel('time')

        plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))
        plt.xticks(rotation=90, fontsize=10)

        # log y axis
        if self.args['log']:
            plt.gca().set_yscale('log')
            plt.ylabel('query duration in ms (log scale)')
        else:
            plt.ylabel('query duration in ms')

        plt.legend(loc='upper left', frameon=False, fontsize=9)
        plt.show()


if __name__ == '__main__':
    mplotqueries = MongoPlotQueries()
    mplotqueries.plot()

"""
mplotqueries LOGFILE [-ns COLL COLL ...]

"""