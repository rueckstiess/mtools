import re
import json
from collections import defaultdict

from .base_section import BaseSection

try:
    from mtools.util.profile_collection import ProfileCollection
except ImportError:
    ProfileCollection = None

# Constants
DELIMITER = "___"
UNKNOWN = "UNKNOWN"

class ClientSection(BaseSection):
    """
    ClientSection class.

    This section goes through the log file and parses two types of log lines:
    (1) client metadata (Driver, Version, App, & IP Address)
    (2) authentication (IP Address & DB User)

    The Connection ID can be used to link the two types of log lines to each
    other, as long as the Connection ID is not reused within the same file.

    For each Driver and Version (2-tuple) or Driver and Version and App
    (3-tuple), it prints out the IPs that connected as well as the DB Users
    that authenticated.
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

        # Dict where the key is a DriverVersionApp and the value is info about
        # the IPs connecting and the Database Users authenticating.
        dva_info = {};

        # Dict where the key is a Connection ID and the value is the
        # DriverVersionApp.
        conn_dva = {}

        # Loop through each log event
        for logevent in self.mloginfo.logfile:
            line = logevent.line_str

            # Order of log file appearance for a given connection:
            # (1) "connection accepted from"
            # (2) "received client metadata"
            # (3) "Successfully authenticated as"

            # If a connection ID is being reused, reset conn_info.
            if line.find("connection accepted from") != -1:

                # Get the connection ID
                conn_id = _parse_connection_accepted_log(logevent)

                # If we've seen the connection ID before, reset the dict.
                if conn_id in conn_dva:
                    print("Connection IDs have reset!")
                    conn_dva = {}

            # Save info from parsing the "client metadata" log line.
            elif line.find("client metadata") != -1:
                dva, ip, conn_id = _parse_client_metadata_log(logevent)

                # Initialize the dva_info dict for this DriverVersionApp
                if dva not in dva_info:
                    dva_info[dva] =  { "ips": {},
                                       "users": {} }

                # Keep track of how many times each IP connected.
                if ip not in dva_info[dva]['ips']:
                    dva_info[dva]['ips'][ip] = 1
                else:
                    dva_info[dva]['ips'][ip] += 1


                # Populate the 'conn_dva' dict mapping the Connection ID to the
                # DriverVersionApp.
                if conn_id not in conn_dva:
                    conn_dva[conn_id] = dva
                else:
                    raise Exception(
                        "Unexpected! This 'client metadata' log line including "
                        "the driver info should have appeared earlier than "
                        "the 'authenticated as' line."
                    )

            # Save info from parsing the connection "authenticated" log line.
            elif line.find("Successfully authenticated as") != -1:
                db_user, conn_id = _parse_authentication_log(logevent)

                # Keep track of how many times each DB User authenticated for
                # by a given DriverVersionApp.
                if conn_id in conn_dva:
                    dva = conn_dva[conn_id]
                    if db_user not in dva_info[dva]['users']:
                        dva_info[dva]['users'][db_user] = 1
                    else:
                        dva_info[dva]['users'][db_user] += 1
                else:
                    # Sometimes there will be no client metadata information
                    # that appears before the 'authenticated as' log line.
                    pass
            else:
                continue

        # Convert the dict values into ordered lists where in particular, the
        # IPs are sorted in descending order by the number of times each IP
        # connected for a given DriverVersionApp.
        for dva, info in sorted(dva_info.items()):
            for type, thing_ct in info.items():
                thing_ct_str_list = [(k, thing_ct[k])
                    for k in sorted(thing_ct, key=thing_ct.get, reverse=True)]
                dva_info[dva][type] = thing_ct_str_list

        # Print the resulting dict
        _print_dva_info(dva_info)

# Print a report for each DriverVersionApp.
def _print_dva_info(dva_info):

    for dva, info in sorted(dva_info.items()):
        db_users_ct = len(info['users'])
        ips_ct = len(info['ips'])

        def _get_printable_str(info_list, unit=""):
            return ", ".join("{} ({}{})".format(*el, unit) for el in info_list)

        # Get a printable string of IPs and the number of times they connected.
        # These should already be sorted in descending order by the number of
        # connections.
        ips_str = _get_printable_str(info['ips'], " conns")

        # Get a printable string of database users and the number of times they
        # authenticated. This will sort them alphabetically by the database
        # user name and undo previous sorting.
        db_users_str = _get_printable_str(sorted(info['users']), " auths")

        # Variable with a string of 79 dashes
        DIVIDER = "-" * 79

        # Print the report
        print("")
        print(DIVIDER)
        print(_get_printable_dva(dva))
        print(DIVIDER)
        print("* DB Users ({}): {}".format(db_users_ct, db_users_str))
        print("* IPs ({}): {}".format(ips_ct, ips_str))
    print("")

# Returns a printable string with information about the Driver, Version, and
# Application Name (if available). The argument to this function is the form
# of <driver>___<version>___<application name>.
def _get_printable_dva(dva):

    if dva == UNKNOWN:
        return dva

    driver, version, app = dva.split(DELIMITER)
    result = "Driver: {} | Version: {}".format(driver, version)
    if app != UNKNOWN:
        result += " | App: {}".format(app)

    return result

# Parse the "received client metadata" log line for the DriverVersionApp, IP,
# and Connection ID.
def _parse_client_metadata_log(logevent):
    driver_version_app = UNKNOWN; app = UNKNOWN;
    line = logevent.line_str

    conn = logevent.conn
    if not conn:
        raise Exception(
            "Expected to get the connection name from the LogEvent.")

    client_metadata = logevent.client_metadata
    if not client_metadata:
        raise Exception(
            "Expected to get the client metadata from the LogEvent.")

    # Get the connection ID
    conn_id = conn.lstrip("conn")

    # Get the Driver x Version x App
    driver = client_metadata['driver']['name']
    version = client_metadata['driver']['version']
    if "application" in client_metadata:
        app = client_metadata['application']['name']
    driver_version_app = "{}{}{}{}{}".format(
        driver, DELIMITER, version, DELIMITER, app)

    # Get the IP
    pos = line.find("client metadata")
    tokens = line[pos:pos + 100].split(" ")
    ip = tokens[3].split(':')[0]

    return driver_version_app, ip, conn_id

# Parse the "connection accepted from" log line for the Connection ID
def _parse_connection_accepted_log(logevent):
    line = logevent.line_str

    pos = line.find("connection accepted from")
    tokens = line[pos:pos + 100].split(" ")
    conn_id = tokens[4].lstrip("#")
    return conn_id

# Parse the "Successfully authenticated as" log line for the DB User and
# the Connection ID.
def _parse_authentication_log(logevent):
    line = logevent.line_str

    pos = line.find(" authenticated as ")
    tokens = line.split(" ")
    db_user = "{}@{}".format(tokens[8], tokens[10])

    pos = line.split(' ')
    conn_id = tokens[3].split("conn")[1].split("]")[0]

    return db_user, conn_id
