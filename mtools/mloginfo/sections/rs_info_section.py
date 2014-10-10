from base_section import BaseSection
from mtools.util.print_table import print_table
from mtools.util import OrderedDict

class RsInfoSection(BaseSection):
    """ This section determines if there is any Replica Set infomation like the replset name in the log file and prints 
        the available information.
    """
    
    name = "rsinfo"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --rsinfo flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--rsinfo', action='store_true', default='true',help='outputs replica set information (defaults to true)')
        self.mloginfo.argparser_sectiongroup.add_argument('--no-rsinfo', action='store_false', dest='rsinfo',help='don\'t outputs replica set information')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['rsinfo']

    def run(self):
        """ run this section and print out information. """


        if self.mloginfo.logfile.repl_set:
            print "    rs name: %s" % self.mloginfo.logfile.repl_set
            print " rs members: %s" % (self.mloginfo.logfile.repl_set_members  if self.mloginfo.logfile.repl_set_members else "unknown")
            print " rs version: %s" % (self.mloginfo.logfile.repl_set_version  if self.mloginfo.logfile.repl_set_version else "unknown")
        else:
            print "  no rs info changes found"
