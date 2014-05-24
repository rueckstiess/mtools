from base_section import BaseSection
from mtools.util.print_table import print_table
from mtools.util import OrderedDict

class RsStateSection(BaseSection):
    """ This section determines if there were any Replica Set state changes in the log file and prints out
        the times and information about the restarts found.
    """
    
    name = "rsstate"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--rsstate', action='store_true', help='outputs information about every detected RS state change')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['rsstate']

    def run(self):
        """ run this section and print out information. """

        titles = ['date', 'host', 'state/message']
        table_rows = []

        for host, state, logevent in self.mloginfo.logfile.rsstate:
            stats = OrderedDict()
            stats['date'] = logevent.datetime.strftime("%b %d %H:%M:%S")
            stats['host'] = host
            stats['state/message'] = state
            table_rows.append(stats)

        print_table(table_rows, titles, uppercase_headers=False)

        if len(self.mloginfo.logfile.rsstate) == 0:
            print "  no rs state changes found"