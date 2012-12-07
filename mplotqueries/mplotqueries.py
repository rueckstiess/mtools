#!/usr/bin/python

import matplotlib.pyplot as plt
from matplotlib.dates import date2num, DateFormatter
import numpy as np
import argparse
import re
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
		
		# extract connection
		self.connection = None
		for i in items:
			match = re.match(r'^\[(conn[^\]]*)\]$', i)
			if match:
				self.connection = match.group(1)
				break

		# extract namespace
		if 'query' in items:
			self.namespace = items[items.index('query')+1]
		else:
			self.namespace = None

		# extract nscanned, ntoreturn, nreturned (if present)
		labels = ['nscanned', 'ntoreturn', 'nreturned']
		for i in items:
			for label in labels:
				if i.startswith('%s:'%label):
					vars(self)[label] = i.split(':')[-1]
					break

		# extract duration
		self.duration = None
		if items[-1].endswith('ms'):
			self.duration = int(items[-1][:-2])


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
		self.parseArgs()

	def parseArgs(self):
		# create parser object
		parser = argparse.ArgumentParser(description='script to plot query times from a logfile')
		
		# positional argument
		parser.add_argument('filename', action='store', help='logfile to parse')
		parser.add_argument('--ns', action='store', nargs='*', metavar='NS', help='namespaces to include in the plot (default=all)')
		parser.add_argument('--exclude-ns', action='store', nargs='*', metavar='NS', help='namespaces to exclude in the plot')

		self.args = vars(parser.parse_args())
		print self.args


	def plot(self):
		durations = defaultdict(list)
		dates = defaultdict(list)

		f = open(self.args['filename'], 'r')
		for line in f:
			if 'query' in line.split():
				query = Query(line)
			else:
				# continue
				query = Query(line)

			if self.args['ns'] == None or query.namespace in self.args['ns']:
				if self.args['exclude_ns'] == None or (not query.namespace in self.args['exclude_ns']):
					durations[query.namespace].append(query.duration)
					dates[query.namespace].append(query.time)

		for ns in dates:
			durations_arr = np.array(durations[ns])
			d = date2num(dates[ns])
			plt.plot_date(d, durations_arr, '.', alpha=0.5, markersize=10, label=ns)

		plt.ylabel('query duration in ms')
		plt.xlabel('time')

		plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d\n%H:%M:%S'))

		plt.xticks(rotation=90, fontsize=10)


		plt.legend()
		plt.show()


if __name__ == '__main__':
	mplotqueries = MongoPlotQueries()
	mplotqueries.plot()

"""
mplotqueries LOGFILE [-ns COLL COLL ...]




"""