#!/usr/bin/python

from mtools.mtoolbox.logline import LogLine
import argparse
import sys

if __name__ == '__main__':
    # create parser object
    parser = argparse.ArgumentParser(description='mongod/mongos log file to json converter. \
        Extracts information from each line of the log file and outputs a json document per line. \
        To import into mongodb, use: mlog2json logfile | mongoimport -d DATABASE -c COLLECTION')
    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='logfile to convert')

    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    for line in logfile:
        print LogLine(line).to_json()

