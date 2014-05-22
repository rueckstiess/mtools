from base_section import BaseSection

from mtools.util.profile_collection import ProfileCollection

class RestartSection(BaseSection):
    """ This section determines if there were any restarts in the log file and prints out
        the times and version of the restarts found. It uses the information collected in
        LogFile so it doesn't have to walk the file manually.
    """
    
    name = "restarts"
    description = "information about every detected restart"


    def run(self):
        if isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return

        for version, logevent in self.mloginfo.logfile.restarts:
            print "   %s version %s" % (logevent.datetime.strftime("%b %d %H:%M:%S"), version)

        if len(self.mloginfo.logfile.restarts) == 0:
            print "  no restarts found"
