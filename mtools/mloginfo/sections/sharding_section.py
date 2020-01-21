from mtools.util.print_table import print_table

from .base_section import BaseSection


class ShardingSection(BaseSection):
    """
    ShardingSection class.

    This section goes through the logfile and extracts any sharding related information
    """

    name = "sharding"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        helptext = 'outputs sharding related information'
        self.mloginfo.argparser_sectiongroup.add_argument('--sharding',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return(self.mloginfo.args['sharding'])

    def run(self):
        """Run this section and print out information."""
        logfile = self.mloginfo.logfile

        if logfile.shards and logfile.csrs:
            print("  Sharding overview:")

            if logfile.binary == "mongos":
                print("    The role of this node (mongos)")
            elif logfile.port in logfile.csrs[1]:
                print("    The role of this node (CSRS)")
            else:
                print("    The role of this node (shard)")

            print("    Shards:")
            for shard_name, replica_set in logfile.shards:
                print(f"      {shard_name}: {replica_set}")

            print("    CSRS:")
            name, replica_set = logfile.csrs
            print(f"      {name}: {replica_set}")
        else:
            print("  No shard info found")
