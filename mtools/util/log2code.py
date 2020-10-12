#!/usr/bin/env python3

import os
import re
# import sys
# import argparse
from itertools import zip_longest
import pickle

import mtools


def import_l2c_db():
    """
    Static import helper function.

    Checks if the log2code.pickle exists first, otherwise raises ImportError.
    """
    data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
    if os.path.exists(os.path.join(data_path, 'log2code.pickle')):
        av, lv, lbw, lcl = pickle.load(open(os.path.join(data_path,
                                                          'log2code.pickle'),
                                             'rb'))
        return av, lv, lbw, lcl
    else:

        raise ImportError('log2code.pickle not found in %s.' % data_path)


class Log2CodeConverter(object):

    # static import of logdb data structures
    all_versions, log_version, logs_by_word, log_code_lines = import_l2c_db()

    def _log2code(self, line):
        tokens = re.split(r'[\s"]', line)

        # find first word in first 20 tokens that has a corresponding
        # log message stored
        for word_no, word in enumerate(w for w in tokens
                                       if w in self.logs_by_word):

            # go through all error messages starting with this word
            coverage = []
            for log in self.logs_by_word[word]:

                if all([line.find(token) >= 0 for token in log]):
                    # all tokens match, calculate coverage
                    cov = sum([len(token) for token in log])
                    coverage.append(cov)
                else:
                    coverage.append(0)

            best_cov = max(coverage)
            if not best_cov:
                continue

            if word_no > 20:
                # avoid parsing really long lines. If the log message didn't
                # start within the first 20 words, it's probably not a
                # known message
                return None

                # no match found, may have been a named log level. try next
                # word.
                # if word in ["warning:", "ERROR:", "SEVERE:", "UNKNOWN:"]:
                #     continue
                # else:
                #     # duration = time.time() - start_time
                #     # print(duration)
                #     continue

            best_match = self.logs_by_word[word][coverage.index(best_cov)]
            return self.log_code_lines[best_match]

    def _strip_counters(self, sub_line):
        """Find the codeline end by taking out the counters and durations."""
        try:
            end = sub_line.rindex('}')
        except ValueError:
            return sub_line
        else:
            return sub_line[:(end + 1)]

    def _strip_datetime(self, sub_line):
        """Strip datetime and other parts so that there is no redundancy."""
        try:
            begin = sub_line.index(']')
        except ValueError:
            return sub_line
        else:
            # create a "" in place character for the beginnings..
            # needed when interleaving the lists
            sub = sub_line[begin + 1:]
            return sub

    def _find_variable(self, pattern, logline):
        """
        Return the variable parts of the code given a tuple of strings pattern.

        Example: (this, is, a, pattern) -> 'this is a good pattern' -> [good]
        """
        var_subs = []
        # find the beginning of the pattern
        first_index = logline.index(pattern[0])
        beg_str = logline[:first_index]
        # strip the beginning substring
        var_subs.append(self._strip_datetime(beg_str))

        for patt, patt_next in zip(pattern[:-1], pattern[1:]):
            # regular expression pattern that finds what's in the middle of
            # two substrings
            pat = re.escape(patt) + '(.*)' + re.escape(patt_next)
            # extract whats in the middle of the two substrings
            between = re.search(pat, logline)
            try:
                # add what's in between if the search isn't none
                var_subs.append(between.group(1))
            except Exception:
                pass
        rest_of_string = logline.rindex(pattern[-1]) + len(pattern[-1])

        # add the rest of the string to end minus the counters and durations
        end_str = logline[rest_of_string:]
        var_subs.append(self._strip_counters(end_str))

        # strip whitespace from each string, but keep the strings themselves
        # var_subs = [v.strip() for v in var_subs]

        return var_subs

    def _variable_parts(self, line, codeline):
        """Return variable parts of the codeline, given the static parts."""
        var_subs = []
        # codeline has pattern and then has the outputs in different versions
        if codeline:
            var_subs = self._find_variable(codeline.pattern, line)
        else:
            # make variable part of the line string without all the other stuff
            line_str = self._strip_datetime(self._strip_counters(line))
            var_subs = [line_str.strip()]
        return var_subs

    def __call__(self, line, variable=False):
        """Return tuple of log2code and variable parts when class is called."""
        if variable:
            log2code = self._log2code(line)
            return log2code, self._variable_parts(line, log2code)
        else:
            return self._log2code(line), None

    def combine(self, pattern, variable):
        """Combine a pattern and variable parts to be a line string again."""
        inter_zip = zip_longest(variable, pattern, fillvalue='')
        interleaved = [elt for pair in inter_zip for elt in pair]
        return ''.join(interleaved)


# class MLog2Code(object):
#
#     def __init__(self):
#         self._import_l2c_db()
#         self._parse_args()
#         self.analyse()
#
#     def _import_l2c_db(self):
#         (self.all_versions, self.logs_versions, self.logs_by_word,
#          self.log_code_lines) = cPickle.load(open('./logdb.pickle', 'rb'))
#
#     def _parse_args(self):
#         # create parser object
#         parser = argparse.ArgumentParser(description=('mongod/mongos log '
#                                                       'file to code line '
#                                                       'converter (BETA)'))
#
#         # only create default argument if not using stdin
#         if sys.stdin.isatty():
#             parser.add_argument('logfile', action='store',
#                                 help=('looks up and prints out information '
#                                       'about where a log line originates '
#                                       'from the code.'))
#
#         self.args = vars(parser.parse_args())
#
#     def analyse(self):
#         # open logfile
#         if sys.stdin.isatty():
#             logfile = open(self.args['logfile'], 'r')
#         else:
#             logfile = sys.stdin
#
#         for i, line in enumerate(logfile):
#             match = self.log2code(line)
#
#             if  match:
#                 print(line, end=' ')
#                 print(self.logs_versions[match])
#                 print(self.log_code_lines[match])
#
#
#     def log2code(self, line):
#         tokens = line.split()
#
#         # find first word in line that has a corresponding log message stored
#         word = next((w for w in tokens if w in self.logs_by_word), None)
#         if not word:
#             return None
#
#         # go through all error messages starting with this word
#         coverage = []
#         for log in self.logs_by_word[word]:
#
#             if all([line.find(token) >= 0 for token in log]):
#                 # all tokens match, calculate coverage
#                 cov = sum([len(token) for token in log])
#                 coverage.append(cov)
#             else:
#                 coverage.append(0)
#
#         best_cov = max(coverage)
#         if not best_cov:
#             return None
#
#         best_match = self.logs_by_word[word][coverage.index(best_cov)]
#         return best_match
#
#
# if __name__ == '__main__':
#     l2cc = Log2CodeConverter()
#     lcl = l2cc('Sun Mar 24 00:44:16.295 [conn7815] moveChunk migrate '
#                'commit accepted by TO-shard: '
#                '{ active: true, ns: "db.coll", from: "shard001:27017", '
#                'min: { i: ObjectId("4b7730748156791f310b03a3"), '
#                'm: "stats", t: new Date(1348272000000) }, '
#                'max: { i: ObjectId("4b8f826192f9e2154d05dda7"), '
#                'm: "mongo", t: new Date(1345680000000) }, '
#                'shardKeyPattern: { i: 1.0, m: 1.0, t: 1.0 }, '
#                'state: "done", counts: { cloned: 3115, '
#                'clonedBytes: 35915282, catchup: 0, '
#                'steady: 0 }, ok: 1.0 }')
#     print lcl.versions
#
#     possible_versions = possible_versions & set(logs_versions[best_match])
#
#     if len(possible_versions) != old_num_v:
#         print(i, line.rstrip())
#         print("    best_match: %s" % best_match)
#         print("    log message only present in versions: %s"
#               % logs_versions[best_match])
#         print("    this limits the possible versions to: %s"
#               % possible_versions)
#         print('')
#
#     if not possible_versions:
#         raise SystemExit
#
#     print("possible versions: "
#           ", ".join([pv[1:] for pv in possible_versions]))
#     for pv in possible_versions:
#         print(pv, possible_versions[pv])
#
#     plt.bar(range(len(possible_versions.values())),
#             possible_versions.values(), align='center')
#     plt.xticks(range(len(possible_versions.keys())),
#                possible_versions.keys(), size='small', rotation=90)
#     plt.show()