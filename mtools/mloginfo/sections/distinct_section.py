from collections import defaultdict

from .base_section import BaseSection
from mtools.util.log2code import Log2CodeConverter

try:
    from mtools.util.profile_collection import ProfileCollection
except ImportError:
    ProfileCollection = None


class DistinctSection(BaseSection):
    """
    DistinctSection class.

    This section shows a distinct view of all log lines matched with the
    Log2Code matcher. It will output sorted statistics of which logevent
    patterns where matched how often (most frequent first).
    """

    name = "distinct"
    log2code = Log2CodeConverter()

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        helptext = ('outputs distinct list of all log line by message '
                    'type (slow)')
        self.mloginfo.argparser_sectiongroup.add_argument('--distinct',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Rreturn boolean if this section is active."""
        return self.mloginfo.args['distinct']

    def run(self):
        """Run each line through log2code and group by matched pattern."""
        if ProfileCollection and isinstance(self.mloginfo.logfile,
                                            ProfileCollection):
            print("\n    not available for system.profile collections\n")
            return

        codelines = defaultdict(lambda: 0)
        non_matches = 0

        # get log file information
        logfile = self.mloginfo.logfile
        if logfile.start and logfile.end and not self.mloginfo.args['verbose']:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) -
                              progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        for i, logevent in enumerate(self.mloginfo.logfile):
            cl, _ = self.log2code(logevent.line_str)

            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if logevent.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(logevent
                                                                     .datetime)
                    (self.mloginfo
                     .update_progress(float(progress_curr - progress_start) /
                                      progress_total))

            if cl:
                codelines[cl.pattern] += 1
            else:
                if logevent.operation:
                    # skip operations (command, insert, update, delete,
                    # query, getmore)
                    continue
                if not logevent.thread:
                    # skip the lines that don't have a thread name
                    # (usually map/reduce or assertions)
                    continue
                if len(logevent.split_tokens) - logevent.datetime_nextpos <= 1:
                    # skip empty log messages (after thread name)
                    continue
                if ("warning: log line attempted" in logevent.line_str and
                        "over max size" in logevent.line_str):
                    # skip lines that are too long
                    continue

                # everything else is a real non-match
                non_matches += 1
                if self.mloginfo.args['verbose']:
                    print("couldn't match:" + logevent)

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        if self.mloginfo.args['verbose']:
            print('')

        for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
            print("%8i  %s" % (codelines[cl], " ... ".join(cl)))

        print('')
        if non_matches > 0:
            print("distinct couldn't match %i lines" % non_matches)
            if not self.mloginfo.args['verbose']:
                print("to show non-matched lines, run with --verbose.")
