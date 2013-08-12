#!/usr/bin/python

from datetime import datetime, timedelta, MINYEAR, MAXYEAR
import argparse, re

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool

class MLogMergeTool(LogFileTool):
    """ Merges several MongoDB log files by their date and time. 
    """

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=False)

        self.argparser.add_argument('--labels', action='store', nargs='*', default=['enum'], help='labels to distinguish original files. Choose from none, enum, alpha, filename, or provide list.')
        self.argparser.add_argument('--pos', action='store', default=0, help="position of label (default=0, front of line, other options are 'eol' or the position as int.")
        self.argparser.add_argument('--timezone', action='store', nargs='*', default=[], type=int, metavar="N", help="timezone adjustments: add N hours to corresponding log file")


    def run(self, arguments=None):
        LogFileTool.run(self, arguments)

        logfiles = self.args['logfile']

        # handle labels parameter
        if len(self.args['labels']) == 1:
            label = self.args['labels'][0]
            if label == 'enum':
                labels = ['{%i}'%(i+1) for i in range(len(logfiles))]
            elif label == 'alpha':
                labels = ['{%s}'%chr(97+i) for i in range(len(logfiles))]
            elif label == 'none':
                labels = [None for _ in logfiles]
            elif label == 'filename':
                labels = ['{%s}'%fn.name for fn in logfiles]
        elif len(self.args['labels']) == len(logfiles):
            labels = self.args['labels']
        else:
            raise SystemExit('Error: Number of labels not the same as number of files.')

        # handle timezone parameter
        if len(self.args['timezone']) == 1:
            self.args['timezone'] = self.args['timezone'] * len(logfiles)

        elif len(self.args['timezone']) == len(logfiles):
            pass

        elif len(self.args['timezone']) == 0:
            self.args['timezone'] = [0] * len(logfiles)

        else:
            raise SystemExit('Error: Invalid number of timezone parameters. Use either one parameter (for global adjustment) or the number of log files (for individual adjustments).')

        # handle position parameter
        position = self.args['pos']
        if position != 'eol':
            position = int(position)

        # define minimum and maximum datetime object
        mindate = datetime(MINYEAR, 1, 1, 0, 0, 0)
        maxdate = datetime(MAXYEAR, 12, 31, 23, 59, 59)

        # open files, read first lines, extract first dates
        lines = [f.readline() for f in logfiles]
        dates = [LogLine(l).datetime for l in lines]
        
        # replace all non-dates with mindate
        dates = [d if d else mindate for d in dates]
        dates = [d + timedelta(hours=self.args['timezone'][i]) for i,d in enumerate(dates) if d]

        while any([l != '' for l in lines]):
            # pick smallest date of all non-empty lines
            condDates = ([d if lines[i] != '' else maxdate for i,d in enumerate(dates)])
            minCondDate = min(condDates)
            minIndex = condDates.index(minCondDate)

            # print out current line
            currLine = lines[minIndex].rstrip()
            try:
                oldDate = minCondDate - timedelta(hours=self.args['timezone'][minIndex])
            except OverflowError:
                oldDate = minCondDate
                
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
            lines[minIndex] = logfiles[minIndex].readline()
            dates[minIndex] = LogLine(lines[minIndex]).datetime


            if not dates[minIndex]:
                dates[minIndex] = mindate 
            else:
                dates[minIndex] += timedelta(hours=self.args['timezone'][minIndex])



if __name__ == '__main__':
    tool = MLogMergeTool()
    tool.run()
