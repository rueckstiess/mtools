from util import extractDateTime
from datetime import datetime, MAXYEAR
import argparse, re

class MongoLogMerger(object):
	def __init__(self):
		pass


	def parse(self):
		# create parser object
		parser = argparse.ArgumentParser(description='mongod/mongos log file merger.')
		parser.add_argument('logfiles', action='store', nargs='*', help='logfiles to merge.')
		# parser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
		parser.add_argument('--labels', action='store', nargs='*', default='enum', help='labels to put in front of line')

		args = vars(parser.parse_args())

		openFiles = [open(f, 'r') for f in args['logfiles']]
		lines = [f.readline() for f in openFiles]
		dates = [extractDateTime(l) for l in lines]

		# define maximum datetime object
		maxdate = datetime(MAXYEAR, 12, 31, 23, 59, 59)

		while any([l != '' for l in lines]):
			# pick smallest date of all non-empty lines
			condDates = ([d if lines[i] != '' else maxdate for i,d in enumerate(dates)])
			minIndex = condDates.index(min(condDates))

			print "{%i}"%minIndex, lines[minIndex],

			# print '{%i}'%minIndex+1 + lines[minIndex],

			lines[minIndex] = openFiles[minIndex].readline()
			dates[minIndex] = extractDateTime(lines[minIndex])

			# end of file reached, print newline
			if lines[minIndex] == '':
				print




if __name__ == '__main__':
	mlogmerge = MongoLogMerger()
	mlogmerge.parse()