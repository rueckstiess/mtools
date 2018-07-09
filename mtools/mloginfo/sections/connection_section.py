import re
from collections import defaultdict

from .base_section import BaseSection

try:
    from mtools.util.profile_collection import ProfileCollection
except ImportError:
    ProfileCollection = None


class ConnectionSection(BaseSection):
    """
    ConnectionSection class.

    This section goes through the logfile and extracts information about
    opened and closed connections.
    """

    name = "connections"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        helptext = 'outputs information about opened and closed connections'
        self.mloginfo.argparser_sectiongroup.add_argument('--connections',
                                                          action='store_true',
                                                          help=helptext)
        helptext = ('outputs helpful statistics for connection '
                    'duration (min/max/avg)')
        self.mloginfo.argparser_sectiongroup.add_argument('--connstats',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return(self.mloginfo.args['connections'] or
               self.mloginfo.args['connstats'])

    def run(self):
        """Run this section and print out information."""
        if ProfileCollection and isinstance(self.mloginfo.logfile,
                                            ProfileCollection):
            print("\n    not available for system.profile collections\n")
            return

        ip_opened = defaultdict(lambda: 0)
        ip_closed = defaultdict(lambda: 0)

        socket_exceptions = 0

        START_TIME_EMPTY = -11
        END_TIME_ALREADY_FOUND = -111
        MIN_DURATION_EMPTY = 9999999999
        MAX_DURATION_EMPTY = -1

        end_connid_pattern = re.compile(r'\[conn(\d+)\]')

        genstats = self.mloginfo.args['connstats']
        if genstats:
            connections_start = defaultdict(lambda: START_TIME_EMPTY)
            ipwise_sum_durations = defaultdict(lambda: 0)
            ipwise_count = defaultdict(lambda: 0)
            ipwise_min_connection_duration = defaultdict(lambda:
                                                         MIN_DURATION_EMPTY)
            ipwise_max_connection_duration = defaultdict(lambda:
                                                         MAX_DURATION_EMPTY)

            min_connection_duration = MIN_DURATION_EMPTY
            max_connection_duration = MAX_DURATION_EMPTY

            sum_durations = 0
            fullconn_counts = 0

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str

            pos = line.find('connection accepted')
            if pos != -1:
                # connection was opened, increase counter
                tokens = line[pos:pos + 100].split(' ')
                if tokens[3] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[3].split(':')
                ip_opened[ip] += 1

                if genstats:
                    connid = tokens[4].strip('#')
                    dt = logevent.datetime

                    # Sanity checks
                    if connid.isdigit() is False or dt is None:
                        continue

                    if connections_start[connid] != START_TIME_EMPTY:
                        errmsg = ("Multiple start datetimes found for the "
                                  "same connection ID. Consider analysing one "
                                  "log sequence.")
                        raise NotImplementedError(errmsg)

                    connections_start[connid] = dt

            pos = line.find('end connection')
            if pos != -1:
                # connection was closed, increase counter
                tokens = line[pos:pos + 100].split(' ')
                if tokens[2] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[2].split(':')
                ip_closed[ip] += 1

                if genstats:

                    # Sanity check
                    if end_connid_pattern.search(line, re.M | re.I) is None:
                        continue

                    # The connection id value is stored just before end
                    # connection -> [conn385] end connection
                    end_connid = (end_connid_pattern.
                                  search(line, re.M | re.I).group(1))
                    dt = logevent.datetime

                    # Sanity checks
                    if (end_connid.isdigit() is False or dt is None or
                            connections_start[end_connid] == START_TIME_EMPTY):
                        continue

                    if connections_start[end_connid] == END_TIME_ALREADY_FOUND:
                        errmsg = ("Multiple end datetimes found for the same "
                                  "connection ID %s. Consider analysing one "
                                  "log sequence.")
                        raise NotImplementedError(errmsg % (end_connid))

                    dur = dt - connections_start[end_connid]
                    dur_in_sec = dur.seconds

                    if dur_in_sec < min_connection_duration:
                        min_connection_duration = dur_in_sec

                    if dur_in_sec > max_connection_duration:
                        max_connection_duration = dur_in_sec

                    if dur_in_sec < ipwise_min_connection_duration[ip]:
                        ipwise_min_connection_duration[ip] = dur_in_sec

                    if dur_in_sec > ipwise_max_connection_duration[ip]:
                        ipwise_max_connection_duration[ip] = dur_in_sec

                    sum_durations += dur.seconds
                    fullconn_counts += 1

                    ipwise_sum_durations[ip] += dur_in_sec
                    ipwise_count[ip] += 1

                    connections_start[end_connid] = END_TIME_ALREADY_FOUND

            if "SocketException" in line:
                socket_exceptions += 1

        # calculate totals
        total_opened = sum(ip_opened.values())
        total_closed = sum(ip_closed.values())

        unique_ips = set(ip_opened.keys())
        unique_ips.update(ip_closed.keys())

        # output statistics
        print("     total opened: %s" % total_opened)
        print("     total closed: %s" % total_closed)
        print("    no unique IPs: %s" % len(unique_ips))
        print("socket exceptions: %s" % socket_exceptions)
        if genstats:
            if fullconn_counts > 0:
                print("overall average connection duration(s): %s"
                      % (sum_durations / fullconn_counts))
                print("overall minimum connection duration(s): %s"
                      % min_connection_duration)
                print("overall maximum connection duration(s): %s"
                      % max_connection_duration)
            else:
                print("overall average connection duration(s): -")
                print("overall minimum connection duration(s): -")
                print("overall maximum connection duration(s): -")
        print('')

        for ip in sorted(unique_ips, key=lambda x: ip_opened[x], reverse=True):
            opened = ip_opened[ip] if ip in ip_opened else 0
            closed = ip_closed[ip] if ip in ip_closed else 0

            if genstats:
                covered_count = (
                    ipwise_count[ip]
                    if ip in ipwise_count
                    else 1)
                connection_duration_ip = (
                    ipwise_sum_durations[ip]
                    if ip in ipwise_sum_durations
                    else 0)
                ipwise_min_connection_duration_final = (
                    ipwise_min_connection_duration[ip]
                    if ipwise_min_connection_duration[ip] != MIN_DURATION_EMPTY
                    else 0)
                ipwise_max_connection_duration_final = (
                    ipwise_max_connection_duration[ip]
                    if ipwise_max_connection_duration[ip] != MAX_DURATION_EMPTY
                    else 0)

                print("%-15s  opened: %-8i  closed: %-8i dur-avg(s): %-8i "
                      "dur-min(s): %-8i dur-max(s): %-8i"
                      % (ip, opened, closed,
                         connection_duration_ip / covered_count,
                         ipwise_min_connection_duration_final,
                         ipwise_max_connection_duration_final))
            else:
                print("%-15s  opened: %-8i  closed: %-8i"
                      % (ip, opened, closed))

        print('')
