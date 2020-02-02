from collections import defaultdict, namedtuple, Counter
from difflib import SequenceMatcher
import re

from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from .base_section import BaseSection

ChunksTuple = namedtuple('ChunksTuple', [
    'time',
    'range',
    'movedFromTo',
    'namespace',
    'migrationStatus',
    'errorMessage'
])

SplitTuple = namedtuple('SplitTuple', [
    'time',
    'range',
    'namespace',
    'numSplits',
    'success',
    'error'
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

        print("\nOverview:\n")

        if logfile.shards and logfile.csrs:

            if logfile.binary == "mongos":
                print("  The role of this node: (mongos)")
            elif logfile.repl_set in logfile.csrs[0]:
                print("  The role of this node: (CSRS)")
            else:
                print("  The role of this node: (shard)")

            print("  Shards:")
            for shard_name, replica_set in logfile.shards:
                print(f"    {shard_name}: {replica_set}")

            print("  CSRS:")
            name, replica_set = logfile.csrs
            print(f"    {name}: {replica_set}")
        else:
            print("  no sharding info found.")

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

            # All common error message is lower case so it can be compared to line content
            common_error_message_content = [
                'failed to update the persisted chunk metadata for collection ... caused by',
                'cannot accept new chunks because there are still ... deletes from previous migration',
                'local document ... has same _id as cloned remote document',
                'local document ... has same _id as reloaded remote document',
                'batch insertion failed'
                '[rangedeleter] waiting for open cursors before removing range',
                'will be scheduled after all possibly dependent queries finish',
                '[collection range deleter] deferring deletion of '
            ]

            if (not any(keyword in logevent.line_str.lower() for keyword in
                        common_error_message_content)):
                continue

            log_tokens = logevent.split_tokens[3:]

            for index, token in enumerate(log_tokens):
                if re.match(r'\'(.+?)\'', token) or any(char.isdigit() for char in token):
                    log_tokens[index] = "..."

            error_log_line = ' '.join(log_tokens)
            error_log_line = re.sub(r' \S+\.\S+ ', ' XXX ', error_log_line)
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

        print("Error Messages:\n")

        if not len(errorlines):
            print("  no error messages found.")
        else:
            for cl in sorted(errorlines, key=lambda x: errorlines[x], reverse=True):
                print("%3i  %s" % (errorlines[cl], cl))

        print("\nChunks Moved From This Shard:\n")
        self._print_chunk_migrations(logfile.chunks_moved_from, moved_from=True)

        print("\nChunks Moved To This Shard:\n")
        self._print_chunk_migrations(logfile.chunks_moved_to)

        print("\nChunk Split Statistics:\n")
        self._print_chunk_statistics()

        print("")

    def _print_chunk_statistics(self):
        """Prints the chunk split statistics in a table"""
        chunk_split_groupings = Grouping(group_by=lambda x: (x.time.strftime("%Y-%m-%dT%H"),
                                                             x.namespace))
        self.mloginfo.logfile.chunk_splits.reverse()
        for chunk_split in self.mloginfo.logfile.chunk_splits:
            time, split_range, namespace, numSplits, success, error = chunk_split
            split_tuple = SplitTuple(time=time,
                                     range=split_range,
                                     namespace=namespace,
                                     numSplits=numSplits,
                                     success=success,
                                     error=error)
            chunk_split_groupings.add(split_tuple)
        
        titles = ['  time (/hour)',
                  'namespace',
                  '# split-vectors issued',
                  'successful chunk splits',
                  'failed chunk splits']
        
        if len(chunk_split_groupings) == 0:
            print("  no chunk splits found.")
        else:
            table_rows = []
            for group, splits in chunk_split_groupings.items():
                time, namespace = group
                successful_count = 0
                total_number_vectors = 0
                split_succeeded_after = dict()
                failed_splits = dict()
                for split in splits:
                    total_number_vectors += int(split.numSplits)
                    if (not split.success) and split.error:
                        count, timestamps = failed_splits.get(split.error, (0, list()))
                        count += 1
                        if split_succeeded_after.get(split.range, False):
                            timestamps.append(split.time.strftime("%H:%M:%S.%f")[:-3] + ' **WAS SUCCESSFUL AFTER**')
                        else:
                            timestamps.append(split.time.strftime("%H:%M:%S.%f")[:-3])
                        failed_splits[split.error] = (count, timestamps)
                    elif split.success:
                        split_succeeded_after[split.range] = True
                        successful_count += 1

                split_summary = OrderedDict()

                split_summary['time'] = f"  {time}"
                split_summary['namespace'] = namespace
                split_summary['numSplitVectors'] = f'{total_number_vectors} split vector(s)'
                split_summary['successfulSplits'] = f"{successful_count} chunk(s) splitted. "

                failed_split = ""
                for error, info in failed_splits.items():
                    count, timestamps = info
                    failed_split += f'{count} chunk(s): {timestamps} failed with "{error}". '

                if len(failed_split):
                    split_summary['failedChunkSplits'] = failed_split
                else:
                    split_summary['failedChunkSplits'] = "no failed chunk splits."

                table_rows.append(split_summary)

            print_table(table_rows, titles)

    def _print_chunk_migrations(self, chunks, moved_from=False):
        chunks.reverse()
        chunk_groupings = Grouping(group_by=lambda x: (x.time.strftime("%Y-%m-%dT%H"),
                                                       x.movedFromTo,
                                                       x.namespace))

        for chunk_moved in chunks:
            time, chunk_range, moved_to_from, namespace, status, error_message = chunk_moved
            moved_tuple = ChunksTuple(time=time,
                                      range=chunk_range,
                                      movedFromTo=moved_to_from,
                                      namespace=namespace,
                                      migrationStatus=status,
                                      errorMessage=error_message)
            chunk_groupings.add(moved_tuple)

        if moved_from:
            titles = ['  time (/hour)',
                      'to shard',
                      'namespace',
                      '# chunks migrations attempted',
                      'successful chunk migrations',
                      'failed chunk migrations']
        else:
            titles = ['  time (/hour)',
                      'from shard',
                      'namespace',
                      '# chunks migrations attempted',
                      'successful chunk migrations',
                      'failed chunk migrations']

        if len(chunk_groupings) == 0:
            print("  no chunk migrations found.")
        else:
            table_rows = []
            for group, chunks in chunk_groupings.items():
                time, moved_to_from, namespace = group

                successful_count = 0
                failed = dict()
                succeeded_after = dict()
                for chunk in chunks:
                    if chunk.migrationStatus == "success":
                        successful_count += 1
                        succeeded_after[chunk.range] = (True, chunk.time)
                    else:
                        count, timestamps = failed.get(chunk.errorMessage, (0, list()))
                        count += 1
                        successful_after, timestamp = succeeded_after.get(chunk.range, (False, None))
                        if successful_after:
                            timestamp = timestamp.strftime("%H:%M:%S.%f")[:-3]
                            timestamps.append(chunk.time.strftime("%H:%M:%S.%f")[:-3] + f' BECAME SUCCESSFUL AT: {timestamp}')
                        else:
                            timestamps.append(chunk.time.strftime("%H:%M:%S.%f")[:-3])
                        failed[chunk.errorMessage] = (count, timestamps)

                moved_chunks = OrderedDict()

                moved_chunks['time'] = f"  {time}"
                moved_chunks['movedFromTo'] = moved_to_from
                moved_chunks['namespace'] = namespace
                moved_chunks['numberOfChunks'] = f'{len(chunks)} chunk(s)'
                moved_chunks['successChunkMigrations'] = f"{successful_count} chunk(s) moved"

                failed_migrations = ""
                for error, info in failed.items():
                    count, timestamps = info
                    failed_migrations += f'{count} chunk(s): {timestamps} failed with "{error}".'

                if len(failed_migrations):
                    moved_chunks['failedChunkMigrations'] = failed_migrations
                else:
                    moved_chunks['failedChunkMigrations'] = "no failed chunks."

                table_rows.append(moved_chunks)

            print_table(table_rows, titles)
