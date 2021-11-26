#!/usr/bin/env python3

from collections import defaultdict


class LogCodeLine(object):
    """
    LogCodeLine represents a logevent pattern extracted from the source code.

    The pattern is a tuple of constant strings, variables are cut out.
    LogCodeLine stores "matches" of the same log pattern from different source
    files and different versions of the code.

    A match is a tuple of (filename, line number, loglevel, trigger). Matches
    are stored in a dictionary with the git tag version as they key, e.g.
    "r2.2.3".

    The import_l2c_db.py tool extracts all such patterns and creates
    LogCodeLines for each pattern.
    """

    def __init__(self, pattern, pattern_id):
        """Constructor takes a pattern, which is a tuple of strings."""
        self.pattern = pattern
        self.pattern_id = pattern_id
        self.versions = set()
        self.matches = defaultdict(list)

    def addMatch(self, version, filename, lineno, loglevel, trigger):
        """
        Add a match to the LogCodeLine.

        Include the version, filename of the source file, the line number, and
        the loglevel.
        """
        self.versions.add(version)
        self.matches[version].append((filename, lineno, loglevel, trigger))

    def __str__(self):
        """
        String representation of a LogCodeLine.

        Outputs all matches of the pattern.
        """
        s = "%s\n" % (" <var> ".join(self.pattern))
        for version in sorted(self.versions):
            for filename, lineno, loglevel, trigger in self.matches[version]:
                s += (f'''{version:>10}: in {filename}:{lineno}, loglevel {loglevel}, trigger {trigger}\n''')
        return s
