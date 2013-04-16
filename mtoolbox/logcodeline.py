from collections import defaultdict

class LogCodeLine(object):
    """ LogCodeLine represents a logline pattern extracted from the source code.
        The pattern is a tuple of constant strings, variables are cut out.
        LogCodeLine stores "occurences" of the same log pattern from different
        source files and different versions of the code. 

        An occurence is a tuple of (filename, line number, loglevel). Occurences
        are stored in a dictionary with the git tag version as they key, e.g. 
        "r2.2.3".

        The import_logdb.py tool extracts all such patterns and creates LogCodeLines 
        for each pattern.
    """

    def __init__(self, pattern):
        """ constructor takes a pattern, which is a tuple of strings. """
        self.pattern = pattern
        self.versions = set()
        self.occurences = defaultdict(list)

    def addOccurence(self, version, filename, lineno, loglevel, trigger):
        """ adding an occurence to the LogCodeLine, including the version, filename
            of the source file, the line number, and the loglevel. 
        """
        self.versions.add(version)
        self.occurences[version].append((filename, lineno, loglevel, trigger))

    def __str__(self):
        """ String representation of a LogCodeLine, outputs all occurences of 
            the pattern.
        """
        s = "%s\n"%(" <var> ".join(self.pattern))
        for version in sorted(self.versions):
            for filename, lineno, loglevel, trigger in self.occurences[version]:
                s += "{:>10}: in {}:{}, loglevel {}, trigger {}\n".format(version, filename, lineno, loglevel, trigger)
        return s

