from collections import defaultdict, namedtuple, Counter
from difflib import SequenceMatcher
import re

from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from .base_section import BaseSection

ChunksTuple = namedtuple('ChunksTuple', [
    'time',
    'movedFromTo',
    'namespace',
    'migrationStatus',
    'errorMessage'
])

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

        if not (logfile.shards and logfile.csrs):
            print("no shard info found")
            return

        print("\nOverview:\n")

        if logfile.binary == "mongos":
            print("  The role of this node (mongos)")
        elif logfile.repl_set in logfile.csrs[0]:
            print("  The role of this node (CSRS)")
        else:
            print("  The role of this node (shard)")

        print("  Shards:")
        for shard_name, replica_set in logfile.shards:
            print(f"    {shard_name}: {replica_set}")

        print("  CSRS:")
        name, replica_set = logfile.csrs
        print(f"    {name}: {replica_set}")

        print("\nError Messages:")

        if logfile.start and logfile.end:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) - progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        errorlines = defaultdict(lambda: 0)

        for i, logevent in enumerate(logfile):

            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if logevent.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(logevent.datetime)

                    if progress_total:
                        (self.mloginfo.update_progress(float(progress_curr - progress_start) /
                         progress_total))

            common_error_message_content = [
                'failed to update the persisted chunk metadata for collection',
                'cannot accept new chunks because there are still',
                'has same _id as cloned remote document',
                'has same _id as reloaded remote document',
                'batch insertion failed'
                '[rangedeleter] waiting for open cursors before removing range',
                'will be scheduled after all possibly dependent queries finish',
                '[collection range deleter] deferring deletion of '
            ]

            if (not any(keyword in logevent.line_str.lower() for keyword in
                        common_error_message_content)):
                continue

            log_tokens = logevent.split_tokens[4:]

            for index, token in enumerate(log_tokens):
                if re.match(r'\'(.+?)\'', token) or any(char.isdigit() for char in token):
                    log_tokens[index] = "..."

            error_log_line = ' '.join(log_tokens)
            error_log_line = re.sub(r'\{.*\}', '...', error_log_line)

            if not errorlines.keys():
                errorlines[error_log_line] += 1
                continue

            similar_error = False
            for errorline in errorlines.keys():
                similar_error = (SequenceMatcher(None, errorline, error_log_line).ratio() >= 0.7)
                if similar_error:
                    errorlines[errorline] += 1
                    break

            if not similar_error:
                errorlines[error_log_line] += 1

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        if not len(errorlines):
            print("no error messages found.")
        else:
            for cl in sorted(errorlines, key=lambda x: errorlines[x], reverse=True):
                print("%3i  %s" % (errorlines[cl], cl))

        print("\nChunks Moved From This Shard:\n")
        self._print_chunk_migrations(logfile.chunks_moved_from, moved_from=True)

        print("\nChunks Moved To This Shard:\n")
        self._print_chunk_migrations(logfile.chunks_moved_to)

    def _print_chunk_migrations(self, chunks, moved_from=False):
        chunk_groupings = Grouping(group_by=lambda x: (x.movedFromTo, x.namespace))

        for chunk_moved in chunks:
            time, moved_to_from, namespace, status, error_message = chunk_moved
            moved_tuple = ChunksTuple(time=time,
                                      movedFromTo=moved_to_from,
                                      namespace=namespace,
                                      migrationStatus=status,
                                      errorMessage=error_message)
            chunk_groupings.add(moved_tuple)

        if moved_from:
            titles = ['time',
                      'to shard',
                      'namespace',
                      'number of chunks migrations attempted',
                      'successful chunk migrations',
                      'failed chunk migrations']
        else:
            titles = ['time',
                      'from shard',
                      'namespace',
                      'number of chunks migrations attempted',
                      'successful chunk migrations',
                      'failed chunk migrations']

        if len(chunk_groupings) == 0:
            print("no chunk migrations found.")
        else:
            table_rows = []
            for group, chunks in chunk_groupings.items():
                moved_to_from, namespace = group

                successful_count = 0
                failed = Counter()
                for chunk in chunks:
                    if chunk.migrationStatus == "success":
                        successful_count += 1
                    else:
                        failed.update({chunk.errorMessage: 1})

                moved_chunks = OrderedDict()

                if len(chunks) > 1:
                    moved_chunks['time'] = f"{chunks[0].time} -> {chunks[len(chunks)-1].time}"
                else:
                    moved_chunks['time'] = f"{chunks[len(chunks)-1].time}"

                moved_chunks['movedFromTo'] = moved_to_from
                moved_chunks['namespace'] = namespace
                moved_chunks['numberOfChunks'] = f'{len(chunks)} chunk(s)'
                moved_chunks['successChunkMigrations'] = f"{successful_count} chunk(s) moved"

                failed_migrations = ""
                for error, count in failed.items():
                    failed_migrations += f'{count} chunk(s) failed with "{error}". '

                if len(failed_migrations):
                    moved_chunks['failedChunkMigrations'] = failed_migrations
                else:
                    moved_chunks['failedChunkMigrations'] = "no failed chunks"

                table_rows.append(moved_chunks)

            print_table(table_rows, titles)
