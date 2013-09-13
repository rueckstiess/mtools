from base_section import BaseSection

from mtools.util.log2code import Log2CodeConverter
from mtools.util.logline import LogLine
from mtools.util.logfile import LogFile

from collections import defaultdict


class DistinctSection(BaseSection):
    """ This section shows a distinct view of all log lines matched with the Log2Code matcher.
    	It will output sorted statistics of which logline patterns where matched how often
    	(most frequent first).
    """
    
    name = "distinct"
    log2code = Log2CodeConverter()


    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--distinct', action='store_true', help='outputs distinct list of all log line by message type (slow)')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['distinct']


    def run(self):
        """ go over each line in the logfile, run through log2code matcher 
            and group by matched pattern.
        """

        codelines = defaultdict(lambda: 0)
        non_matches = 0

        # rewind log file in case other sections are walking the lines
        self.mloginfo.logfileOpen.seek(0, 0)

        # get log file information
        lfinfo = LogFile(self.mloginfo.logfileOpen)
        progress_start = self.mloginfo._datetime_to_epoch(lfinfo.start)
        progress_total = self.mloginfo._datetime_to_epoch(lfinfo.end) - progress_start

        for i, line in enumerate(self.mloginfo.logfileOpen):
            cl = self.log2code(line)

            # update progress bar every 1000 lines
            if i % 1000 == 0:
                ll = LogLine(line)
                progress_curr = self.mloginfo._datetime_to_epoch(ll.datetime)
                self.mloginfo.update_progress(float(progress_curr-progress_start) / progress_total)

            if cl:
                codelines[cl.pattern] += 1
            else:
                ll = LogLine(line)
                if ll.operation:
                    # skip operations (command, insert, update, delete, query, getmore)
                    continue
                if not ll.thread:
                    # skip the lines that don't have a thread name (usually map/reduce or assertions)
                    continue
                if len(ll.split_tokens) - ll._thread_offset <= 1:
                    # skip empty log messages (after thread name)
                    continue

                # everything else is a real non-match
                non_matches += 1
                if self.mloginfo.args['verbose']:
                    print "couldn't match:", line,

        # clear progress bar again
        self.mloginfo.update_progress(1.0)

        if self.mloginfo.args['verbose']: 
            print

        for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
            print "%8i"%codelines[cl], "  ", " ... ".join(cl)

        print
        if non_matches > 0:
            print "distinct couldn't match %i lines"%non_matches
            if not self.mloginfo.args['verbose']:
                print "to show non-matched lines, run with --verbose."
