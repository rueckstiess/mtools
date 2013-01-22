#!/usr/bin/python

from mtools.mtoolbox.extractdate import extractDateTime
from datetime import datetime, timedelta, MINYEAR, MAXYEAR
import argparse, re

class MongoLogMerger(object):
	""" Merges several MongoDB log files by their date and time. 
		currently implemented options:
			logfiles          list of logfiles to merge
            -l, --labels      can be any of 'enum', 'alpha', 'none', 'filename', or a list of labels (must be same length as number of files)
            -p, --pos         position of label (default: 0, beginning of line). Another good choice is 5, putting the label behind the [] token, or 'eol'

        planned options:
            logfiles          can be any pattern, like "*.log"
            -r                scan recursive in subfolders for pattern 
            -v, --verbose     more output on top (e.g. which file has which label)
            -c, --color       outputs different files in different colors

    """

	def merge(self):
		# create parser object
		parser = argparse.ArgumentParser(description='mongod/mongos log file merger.')
		parser.add_argument('logfiles', action='store', nargs='*', help='logfiles to merge.')
		# parser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
		parser.add_argument('--labels', action='store', nargs='*', default=['enum'], help='labels to distinguish original files')
		parser.add_argument('--pos', action='store', default=4, help="position of label (0 = front of line, other options are # or 'eol'")
		parser.add_argument('--timezone', action='store', nargs='*', default=[], type=int, metavar="N", help="timezone adjustments: add N hours to corresponding log file")

		args = vars(parser.parse_args())

		# handle logfiles parameter
		logfiles = args['logfiles']

		# handle labels parameter
		if len(args['labels']) == 1:
			label = args['labels'][0]
			if label == 'enum':
				labels = ['{%i}'%(i+1) for i in range(len(logfiles))]
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

		# handle timezone parameter
		if len(args['timezone']) == 1:
			args['timezone'] = args['timezone'] * len(logfiles)

		elif len(args['timezone']) == len(logfiles):
			pass

		elif len(args['timezone']) == 0:
			args['timezone'] = [0] * len(logfiles)

		else:
			raise SystemExit('Error: Invalid number of timezone parameters. Use either one parameter (for global adjustment) or the number of log files (for individual adjustments).')

		# handle position parameter
		position = args['pos']
		if position != 'eol':
			position = int(position)

		# define minimum and maximum datetime object
		mindate = datetime(MINYEAR, 1, 1, 0, 0, 0)
		maxdate = datetime(MAXYEAR, 12, 31, 23, 59, 59)

		# open files, read first lines, extract first dates
		openFiles = [open(f, 'r') for f in args['logfiles']]
		lines = [f.readline() for f in openFiles]
		dates = [extractDateTime(l) for l in lines]
		
		# replace all non-dates with mindate
		dates = [d if d else mindate for d in dates]

		dates = [d + timedelta(hours=args['timezone'][i]) for i,d in enumerate(dates) if d]


		while any([l != '' for l in lines]):
			# pick smallest date of all non-empty lines
			condDates = ([d if lines[i] != '' else maxdate for i,d in enumerate(dates)])
			minCondDate = min(condDates)
			minIndex = condDates.index(minCondDate)

			# print out current line
			currLine = lines[minIndex].rstrip()
			oldDate = minCondDate - timedelta(hours=args['timezone'][minIndex])
			if minCondDate != mindate:
				currLine = currLine.replace(oldDate.strftime('%a %b %d %H:%M:%S'), minCondDate.strftime('%a %b %d %H:%M:%S'))

			if labels[minIndex]:
				if position == 0 or minCondDate == mindate:
					print labels[minIndex], currLine
				elif position == 'eol':
					print currLine, labels[minIndex]
				else:
					tokens = currLine.split()
					print " ".join(tokens[:position]), labels[minIndex], " ".join(tokens[position:])


			else:
				print currLine

			# update lines and dates for that line
			lines[minIndex] = openFiles[minIndex].readline()
			dates[minIndex] = extractDateTime(lines[minIndex])


			if not dates[minIndex]:
				dates[minIndex] = mindate 
			else:
				dates[minIndex] += timedelta(hours=args['timezone'][minIndex])

			# end of file reached, print newline
			# if position != 'eol' and lines[minIndex] == '':
			# 	print

		# close files
		for f in openFiles:
			f.close()


if __name__ == '__main__':
	mlogmerge = MongoLogMerger()
	mlogmerge.merge()