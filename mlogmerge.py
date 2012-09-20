#!/usr/bin/python

from util import extractDateTime
from datetime import datetime, MINYEAR, MAXYEAR
import argparse, re

class MongoLogMerger(object):
	""" Merges several MongoDB log files by their date and time. 
		currently implemented options:
			logfiles          list of logfiles to merge
            -l, --labels      can be any of 'enum', 'alpha', 'none', 'filename', or a list of labels (must be same length as number of files)

        planned options:
            logfiles          can be any pattern, like "*.log"
            -r                scan recursive in subfolders for pattern 
            -v, --verbose     more output on top (e.g. which file has which label)
            -c, --color       outputs different files in different colors
            -p, --pos         position of label (default: 0, beginning of line). Another good choice is 5, putting the label behind the [...] token

    """

	def merge(self):
		# create parser object
		parser = argparse.ArgumentParser(description='mongod/mongos log file merger.')
		parser.add_argument('logfiles', action='store', nargs='*', help='logfiles to merge.')
		# parser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
		parser.add_argument('--labels', action='store', nargs='*', default=['enum'], help='labels to put in front of line')

		args = vars(parser.parse_args())

		# handle logfiles parameter
		logfiles = args['logfiles']

		# handle labels parameter
		if len(args['labels']) == 1:
			label = args['labels'][0]
			if label == 'enum':
				labels = ['{%i}'%i for i in range(len(logfiles))]
			elif label == 'alpha':
				labels = ['{%s}'%chr(97+i) for i in range(len(logfiles))]
			elif label == 'none':
				labels = [None for _ in logfiles]
			elif label == 'filename':
				labels = ['{%s}'%fn for fn in logfiles]
		elif len(args['labels']) == len(logfiles):
			labels = args['labels']
		else:
			raise SystemExit('Error: Number of labels not the same as number of files.')
		print labels


		# define minimum and maximum datetime object
		mindate = datetime(MINYEAR, 1, 1, 0, 0, 0)
		maxdate = datetime(MAXYEAR, 12, 31, 23, 59, 59)

		# open files, read first lines, extract first dates
		openFiles = [open(f, 'r') for f in args['logfiles']]
		lines = [f.readline() for f in openFiles]
		dates = [extractDateTime(l) for l in lines]

		# replace all non-dates with mindate
		dates = [d if d else mindate for d in dates]

		while any([l != '' for l in lines]):
			# pick smallest date of all non-empty lines
			condDates = ([d if lines[i] != '' else maxdate for i,d in enumerate(dates)])
			minIndex = condDates.index(min(condDates))

			if labels[minIndex]:
				print labels[minIndex], lines[minIndex],
			else:
				print lines[minIndex],

			# print '{%i}'%minIndex+1 + lines[minIndex],

			lines[minIndex] = openFiles[minIndex].readline()
			dates[minIndex] = extractDateTime(lines[minIndex])
			if not dates[minIndex]:
				dates[minIndex] = mindate 

			# end of file reached, print newline
			if lines[minIndex] == '':
				print

		# close files
		for f in openFiles:
			f.close()


if __name__ == '__main__':
	mlogmerge = MongoLogMerger()
	mlogmerge.merge()