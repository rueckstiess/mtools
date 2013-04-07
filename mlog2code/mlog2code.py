#!/usr/bin/python

import cPickle
import re
import sys
import argparse
from collections import defaultdict, OrderedDict
from itertools import chain
from matplotlib import pyplot as plt
from extract import LogCodeLine

# from extract import get_all_versions

if __name__ == '__main__':
    all_versions, logs_versions, logs_by_word, log_code_lines = cPickle.load(open('/Users/tr/Documents/code/mtools/mlog2code/logs_versions.pickle', 'rb'))

    # create parser object
    parser = argparse.ArgumentParser(description='mongod/mongos log file to code line converter (BETA)')

    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='looks up and prints out information about where a log line originates from in the code.')

    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    for i, line in enumerate(logfile): 
        tokens = line.split()

        # find first word in line that has a corresponding log message stored
        word = next((w for w in tokens if w in logs_by_word), None)
        if not word:
            continue

        # go through all error messages starting with this word
        coverage = []
        for log in logs_by_word[word]:

            if all([line.find(token) >= 0 for token in log]):
                # all tokens match, calculate coverage
                cov = sum([len(token) for token in log])
                coverage.append(cov)
            else:
                coverage.append(0)
        
        best_cov = max(coverage)
        if not best_cov:
            continue
        
        best_match = logs_by_word[word][coverage.index(best_cov)]
        
        print log_code_lines[best_match]

        #possible_versions = possible_versions & set(logs_versions[best_match])


        # if len(possible_versions) != old_num_v:
        #     print i, line.rstrip()
        #     print "    best_match:", best_match
        #     print "    log message only present in versions:", logs_versions[best_match]
        #     print "    this limits the possible versions to:", possible_versions
        #     print

        # if not possible_versions:
        #     raise SystemExit


    # print "possible versions:", ", ".join([pv[1:] for pv in possible_versions])
    # for pv in possible_versions:
    #     print pv, possible_versions[pv]

    # plt.bar(range(len(possible_versions.values())), possible_versions.values(), align='center')
    # plt.xticks(range(len(possible_versions.keys())), possible_versions.keys(), size='small', rotation=90)
    # plt.show()

