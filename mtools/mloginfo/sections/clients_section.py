import re
import json
from collections import defaultdict

from .base_section import BaseSection

try:
    from mtools.util.profile_collection import ProfileCollection
except ImportError:
    ProfileCollection = None


class ClientSection(BaseSection):
    """
    ClientSection class.

    This section goes through the logfile and extracts driver information from
    connected clients.
    """

    name = "clients"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        helptext = 'outputs client driver information'
        self.mloginfo.argparser_sectiongroup.add_argument('--clients',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return(self.mloginfo.args['clients'])

    def run(self):
        """Run this section and print out information."""
        if ProfileCollection and isinstance(self.mloginfo.logfile,
                                            ProfileCollection):
            print("\n    not available for system.profile collections\n")
            return

        """dictionary variable to hold driver name + version as key and each ip
        appended to a list for value against key"""
        driver_info = {}

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str
            pos = line.find('client metadata')
            if pos != -1:

                tokens = line[pos:pos + 100].split(' ')
                ip, _ = tokens[3].split(':')
                ip_formatted = str(ip)

                if ip_formatted != "127.0.0.1":
                    client_metadata = logevent.client_metadata
                    try:
                        driver = client_metadata["driver"]["name"]
                        version = client_metadata["driver"]["version"]
                        dv_formatted = str(driver) + ":" + str(version)
                        if dv_formatted not in driver_info:
                            driver_info[dv_formatted] = [ip_formatted]
                        elif dv_formatted in driver_info:
                            if ip_formatted in driver_info.get(dv_formatted):
                                continue
                            else:
                                driver_info[dv_formatted].append(ip_formatted)
                    except Exception:
                        next

        print('%-15s - Unique connections' % 'Driver:Version ')
        if len(driver_info):
            for key, value in sorted(driver_info.items()):
                print("%-15s : " % (key) + str(value))
        else:
            print("No client metadata found")
        print('')
