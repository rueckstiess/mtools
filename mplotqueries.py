import matplotlib.pyplot as plt
import numpy as np
import argparse
import re
from util import extractDateTime


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
		self.namespace = items[items.index('query')+1]

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
		self.args = {'filename':'/Users/tr/Documents/tickets/CS-5088/long_queries.txt'}


	def plot(self):
		durations = []
		labels = []

		f = open(self.args['filename'], 'r')
		for line in f:
			if 'query' in line.split():
				query = Query(line)
			else:
				continue

			durations.append(query.duration)
			labels.append(query.time)

		labels = np.array(labels)
		durations = np.array(durations)

		plt.plot(durations, '.')

		grid = [int(g) for g in np.mgrid[:len(labels):30j]]
		grid[-1] -= 1

		plt.xticks(grid, labels[grid], rotation=90, fontsize=10)
		plt.show()


if __name__ == '__main__':
	mplotqueries = MongoPlotQueries()
	mplotqueries.plot()

"""
mplotqueries LOGFILE [-ns COLL COLL ...] [--slow TIME]




"""