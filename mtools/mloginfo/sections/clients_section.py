import re
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

    name = "client driver info"

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

        driver_info = {}

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str



            pos = line.find('client metadata')
            if pos != -1:
                tokens = line[pos:pos + 130].split(' ')
                #handle mgo as driver and verion backwards
                ip, _ = tokens[3].split(':')
                ip_formatted = str(ip)
                print(tokens)
                if tokens[6] == 'driver:' and tokens[10] == 'version:':
                    print("hit1")
                    driver = tokens[9]
                    version = tokens[11]
                    dv_formatted = str(driver[1:-2])+":"+str(version[1:-1])
                    if dv_formatted not in driver_info:
                        driver_info[dv_formatted] = [ip_formatted]
                    elif dv_formatted in driver_info:
                        if ip_formatted in driver_info.get(dv_formatted):
                            continue
                        else:
                            driver_info[dv_formatted].append(ip_formatted)
                elif tokens[9] == '\"MongoDB' and tokens[10] == 'Internal':
                    print("hit2")
                    driver = 'MongoDB Internal Driver'
                    version = tokens[13]
                    dv_formatted = str(driver)+":"+str(version[1:-1])
                    if dv_formatted not in driver_info:
                        driver_info[dv_formatted] = [ip_formatted]
                    elif dv_formatted in driver_info:
                        if ip_formatted in driver_info.get(dv_formatted):
                            continue
                        else:
                            driver_info[dv_formatted].append(ip_formatted)
                elif tokens[9] == '\"mgo\"':
                    print("hit3")
                    driver = tokens[9]
                    version = tokens[11]
                    dv_formatted = str(driver[1:-2])+":"+str(version[1:-1])
                    if dv_formatted not in driver_info:
                        driver_info[dv_formatted] = [ip_formatted]
                    elif dv_formatted in driver_info:
                        if ip_formatted in driver_info.get(dv_formatted):
                            continue
                        else:
                            driver_info[dv_formatted].append(ip_formatted)




        print('%-15s - Unique connections'%'Driver:Version ')
        for key, value in sorted(driver_info.items()):
            print("%-15s : "
                  % (key) + str(value))
        print('')
