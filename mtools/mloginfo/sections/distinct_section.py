from collections import defaultdict

from .base_section import BaseSection
from mtools.util.logformat import LogFormat

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

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        helptext = ('outputs distinct list of all log line by message ')
        self.mloginfo.argparser_sectiongroup.add_argument('--distinct',
                                                          action='store_true',
                                                          help=helptext)

        helptext = ('minimum number of occurences to include in --distinct (default: 5)')
        self.mloginfo.argparser_sectiongroup.add_argument('--distinctmin',
                                                          action='store',
                                                          type=int,
                                                          default=5,
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['distinct']

    def run(self):
        """Group by matched pattern."""
        # get log file information
        logfile = self.mloginfo.logfile

        if logfile.logformat != LogFormat.LOGV2:
            print(f"\nERROR: unsupported log format: {logfile.logformat}\n")
            return

        if logfile.start and logfile.end and not self.mloginfo.args['verbose']:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) -
                              progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        codelines = defaultdict(lambda: 0)
        non_matches = 0

        for i, logevent in enumerate(self.mloginfo.logfile):
            cl = {
                'pattern': f"{logevent.doc.get('msg')}"
            }

            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if logevent.datetime:
                    try:
                        progress_curr = self.mloginfo._datetime_to_epoch(logevent
                                                                        .datetime)
                        (self.mloginfo
                        .update_progress(float(progress_curr - progress_start) /
                                        progress_total))
                    except Exception as e:
                        if self.mloginfo.args['verbose']:
                            print(f"update_progress() exception: {e.msg}")

            if not self.mloginfo.args['verbose']:
                # Skip some generally uninteresting lines
                if logevent.doc.get('ctx') in ('initandlisten','WTCheckpointThread'):
                    non_matches += 1
                else:
                    codelines[cl.get('pattern')] += 1
            else:
                codelines[cl.get('pattern')] += 1

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        if self.mloginfo.args['verbose']:
            print('')

        for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
            if not self.mloginfo.args['verbose'] and codelines[cl] < self.mloginfo.args['distinctmin']:
                non_matches += codelines[cl]
            else:
                print("%8i  %s" % (codelines[cl], cl))

        print('')
        if non_matches > 0:
            print(f"Distinct ignored {non_matches} less informative lines")
            if not self.mloginfo.args['verbose']:
                print("To show ignored lines, run with --verbose")
