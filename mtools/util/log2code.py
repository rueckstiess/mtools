import cPickle
import os
import re
import sys
import argparse
from collections import defaultdict, OrderedDict
from itertools import chain

from mtools.util.logcodeline import LogCodeLine
import mtools

def import_logdb():
    """ static import helper function, checks if the logdb exists first, otherwise
        raises ImportError. 
    """
    data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
    if os.path.exists(os.path.join(data_path, 'logdb.pickle')):
        av, lv, lbw, lcl = cPickle.load(open(os.path.join(data_path, 'logdb.pickle'), 'rb'))
        return av, lv, lbw, lcl
    else:
        raise ImportError('logdb.pickle not found in %s.'%path)


class Log2CodeConverter(object):

    # static import of logdb data structures
    all_versions, log_version, logs_by_word, log_code_lines = import_logdb()
        
    def _log2code(self, line):
        tokens = re.split(r'[\s"]', line)

        # find first word in first 20 tokens that has a corresponding log message stored
        for word_no, word in enumerate(w for w in tokens if w in self.logs_by_word):

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
                # avoid parsing really long lines. If the log message didn't start within the
                # first 20 words, it's probably not a known message
                return None

                # # no match found, may have been a named log level. try next word
                # if word in ["warning:", "ERROR:", "SEVERE:", "UNKNOWN:"]:
                #     continue
                # else:
                #     # duration = time.time() - start_time
                #     # print duration
                #     continue
        
            best_match = self.logs_by_word[word][coverage.index(best_cov)]
            return self.log_code_lines[best_match]

    def __call__(self, line):
        return self._log2code(line)








# class MLog2Code(object):

#     def __init__(self):
#         self._import_logdb()
#         self._parse_args()
#         self.analyse()

#     def _import_logdb(self):
#         self.all_versions, self.logs_versions, self.logs_by_word, self.log_code_lines = \
#             cPickle.load(open('./logdb.pickle', 'rb'))

#     def _parse_args(self):
#         # create parser object
#         parser = argparse.ArgumentParser(description='mongod/mongos log file to code line converter (BETA)')

#         # only create default argument if not using stdin
#         if sys.stdin.isatty():
#             parser.add_argument('logfile', action='store', help='looks up and prints out information about where a log line originates from the code.')

#         self.args = vars(parser.parse_args())

#     def analyse(self):
#         # open logfile
#         if sys.stdin.isatty():
#             logfile = open(self.args['logfile'], 'r')
#         else:
#             logfile = sys.stdin

#         for i, line in enumerate(logfile): 
#             match = self.log2code(line)

#             if  match:
#                 print line,
#                 print self.logs_versions[match]
#                 print self.log_code_lines[match]


#     def log2code(self, line):
#         tokens = line.split()

#         # find first word in line that has a corresponding log message stored
#         word = next((w for w in tokens if w in self.logs_by_word), None)
#         if not word:
#             return None

#         # go through all error messages starting with this word
#         coverage = []
#         for log in self.logs_by_word[word]:

#             if all([line.find(token) >= 0 for token in log]):
#                 # all tokens match, calculate coverage
#                 cov = sum([len(token) for token in log])
#                 coverage.append(cov)
#             else:
#                 coverage.append(0)
        
#         best_cov = max(coverage)
#         if not best_cov:
#             return None
        
#         best_match = self.logs_by_word[word][coverage.index(best_cov)]
#         return best_match



# if __name__ == '__main__':
#         l2cc = Log2CodeConverter()
#         lcl = l2cc("""Sun Mar 24 00:44:16.295 [conn7815] moveChunk migrate commit accepted by TO-shard: { active: true, ns: "db.coll", from: "shard001:27017", min: { i: ObjectId('4b7730748156791f310b03a3'), m: "stats", t: new Date(1348272000000) }, max: { i: ObjectId('4b8f826192f9e2154d05dda7'), m: "mongo", t: new Date(1345680000000) }, shardKeyPattern: { i: 1.0, m: 1.0, t: 1.0 }, state: "done", counts: { cloned: 3115, clonedBytes: 35915282, catchup: 0, steady: 0 }, ok: 1.0 }""")
#         print lcl.versions

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

