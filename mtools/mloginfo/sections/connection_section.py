from base_section import BaseSection
from collections import defaultdict
import re

from mtools.util.profile_collection import ProfileCollection

class ConnectionSection(BaseSection):
    """ This section goes through the logfile and extracts information 
        about opened and closed connections.
    """
    
    name = "connections"
    description = "information about opened and closed connections"


    def run(self):
        """ run this section and print out information. """
        if isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return

        ip_opened = defaultdict(lambda: 0)
        ip_closed = defaultdict(lambda: 0)
        socket_exceptions = 0

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str
            pos = line.find('connection accepted')
            if pos != -1:
                # connection was opened, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[3] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[3].split(':')
                ip_opened[ip] += 1

            pos = line.find('end connection')
            if pos != -1:
                # connection was closed, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[2] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[2].split(':')
                ip_closed[ip] += 1

            if "SocketException" in line:
                socket_exceptions += 1


        # calculate totals
        total_opened = sum(ip_opened.values())
        total_closed = sum(ip_closed.values())

        unique_ips = set(ip_opened.keys())
        unique_ips.update(ip_closed.keys())


        # output statistics
        print "     total opened:", total_opened
        print "     total closed:", total_closed
        print "    no unique IPs:", len(unique_ips)
        print "socket exceptions:", socket_exceptions
        print

        for ip in sorted(unique_ips, key=lambda x: ip_opened[x], reverse=True):
            opened = ip_opened[ip] if ip in ip_opened else 0
            closed = ip_closed[ip] if ip in ip_closed else 0

            print "%-15s  opened: %-8i  closed: %-8i" % (ip, opened, closed)
        print
