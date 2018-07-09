from .base_section import BaseSection


class RsInfoSection(BaseSection):
    """
    RsInfoSection class.

    This section determines if there is any Replica Set infomation like the
    replset name in the log file and prints the available information.
    """

    name = "rsinfo"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --rsinfo flag to argparser
        helptext = 'outputs replica set config information'
        self.mloginfo.argparser_sectiongroup.add_argument('--rsinfo',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['rsinfo']

    def run(self):
        """Run this section and print out information."""
        if self.mloginfo.logfile.repl_set:
            print("    rs name: %s" % self.mloginfo.logfile.repl_set)
            print(" rs members: %s"
                  % (self.mloginfo.logfile.repl_set_members
                     if self.mloginfo.logfile.repl_set_members
                     else "unknown"))
            print(" rs version: %s"
                  % (self.mloginfo.logfile.repl_set_version
                     if self.mloginfo.logfile.repl_set_version
                     else "unknown"))
            print("rs protocol: %s"
                  % (self.mloginfo.logfile.repl_set_protocol
                     if self.mloginfo.logfile.repl_set_protocol
                     else "unknown"))
        else:
            print("  no rs info changes found")
