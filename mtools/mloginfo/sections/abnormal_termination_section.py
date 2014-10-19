from base_section import BaseSection
from mtools.util.print_table import print_table
from mtools.util import OrderedDict
from mtools.util.logevent import LogEvent

class AbnormalTerminationSection(BaseSection):
    """ This section determines if there were any abnormal stops in the log file and prints out
        the times and information about any such events.
    """
    
    name = "Abnormal Termination"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --hardstops flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--hardstops',
                                                          action='store_true',
                                                          help='outputs information about every abnormal termination')

    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['hardstops']

    def run(self):
        """ run this section and print out information. """

        titles = ['date', 'line#', 'line', 'restart']
        table_rows = []

        for termination in self.mloginfo.logfile.abnormal_terminations:
            stats = OrderedDict()
            if termination.termination_event.datetime is not None:
                stats['date'] = termination.termination_event.datetime.strftime("%b %d %H:%M:%S")
            else:
                stats['date'] = termination.restart_event.datetime.strftime("%b %d %H:%M:%S")
            stats['line#'] = termination.line_no
            stats['line'] = termination.termination_event.line_str
            stats['restart'] = termination.restart
            table_rows.append(stats)

        print_table(table_rows, titles, uppercase_headers=False)

        if not self.mloginfo.logfile.abnormal_terminations:
            print "  no abnormal terminations found"


class AbnormalTermination(object):
    """ wrapper class for log files, either as open file streams of from stdin. """

    def __init__(self, termination, restart, line_no):
        """ provide logfile as open file stream or stdin. """
        self._termination = termination
        self._restart = restart
        self._line_no = line_no
        self._log_event = None
        self._restart_event = None

    @property
    def termination_event(self):
        """ provide logfile as open file stream or stdin. """
        if not self._log_event:
            self._log_event = LogEvent(self._termination)
        return self._log_event

    @property
    def restart_event(self):
        """ provide logfile as open file stream or stdin. """
        if not self._restart_event:
            self._restart_event = LogEvent(self._restart)
        return self._restart_event

    @property
    def line_no(self):
        return self._line_no

    @property
    def restart(self):
        return self._restart

    # ignore the following lines w.r.t abnormal terminations
    SKIP = ['***** SERVER RESTARTED *****',
            'Trying to start Windows service',
            'BackgroundJob starting: DataFileSync',
            'Service running',
            'warning: No SSL certificate validation',
            'BackgroundJob starting: DataFileSync',
            'versionCmpTest passed',
            'versionArrayTest passed',
            'shardKeyTest passed',
            'Matcher::matches() { ',
            'shardObjTest passed',
            'isInRangeTest passed',
            'security key:']

    @staticmethod
    def matches(line):
        """ Check if line looks like a date and is not something that should be ignored"""
        line = line.strip()
        m = len(line) >= 4 and line[:3] == '201' or line[:3] in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if any(skip in line for skip in AbnormalTermination.SKIP):
            return False
        else:
            return m

    @staticmethod
    def is_start(line):
        """ Check if line looks like a start message """
        return 'MongoDB starting' in line

    @staticmethod
    def is_stop(line):
        """ Check if line looks a dbexit"""
        return 'dbexit: ' in line
