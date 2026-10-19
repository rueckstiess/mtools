#!/usr/bin/env python3
"""Log counter extraction for LogEvent."""

from mtools.util.logformat import LogFormat


class CountersMixin(object):
    """Read nscanned and the other counters from a legacy log line."""

    @property
    def nscanned(self):
        """Extract nscanned or keysExamined counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscanned

    @property
    def timeActiveMicros(self):
        """Extract timeActiveMicros if available (lazy)."""

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeActiveMicros

    @property
    def timeInactiveMicros(self):
        """Extract timeInactiveMicros if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeInactiveMicros

    @property
    def nscannedObjects(self):
        """
        Extract counters if available (lazy).
        Looks for nscannedObjects or docsExamined.
        """
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nscannedObjects

    @property
    def ntoreturn(self):
        """Extract ntoreturn counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ntoreturn

    @property
    def writeConflicts(self):
        """Extract ntoreturn counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._writeConflicts

    @property
    def nreturned(self):
        """
        Extract counters if available (lazy).
        Looks for nreturned, nReturned, or nMatched counter.
        """
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nreturned

    @property
    def terminationCause(self):

        # Looks for terminationCause counter in Transaction logs.

        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._terminationCause

    @property
    def ninserted(self):
        """Extract ninserted or nInserted counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ninserted

    @property
    def bytesRead(self):
        """Extract bytesRead counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._bytesRead

    @property
    def bytesWritten(self):
        """Extract bytesWritten counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._bytesWritten

    @property
    def timeReadingMicros(self):
        """Extract timeReadingMicros counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeReadingMicros

    @property
    def timeWritingMicros(self):
        """Extract timeWritingMicros counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._timeWritingMicros

    @property
    def ndeleted(self):
        """Extract ndeleted or nDeleted counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._ndeleted

    @property
    def allowDiskUse(self):
        """Extract allowDiskUse counter for aggregation if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._allowDiskUse

    @property
    def nupdated(self):
        """Extract nupdated or nModified counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._nupdated

    @property
    def numYields(self):
        """Extract numYields counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._numYields

    @property
    def readTimestamp(self):
        """Extract readTimeStamp counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._readTimestamp

    @property
    def planSummary(self):
        """Extract planSummary if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._planSummary

    @property
    def actualPlanSummary(self):
        """Extract planSummary including JSON if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._actualPlanSummary

    @property
    def r(self):
        """Extract read lock (r) counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._r

    @property
    def lsid(self):
        """Extract lsid counter if available (lazy)."""
        self._lsid = self._find_pattern('lsid: ', actual=True)
        return self._lsid

    @property
    def locks(self):
        """Extract locks counter for transactions if available (lazy)."""
        self._locks = self._find_pattern('locks:', actual=True)

        return self._locks

    @property
    def txnNumber(self):
        """Extract txnNumber counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._txnNumber

    @property
    def autocommit(self):
        """Extract autocommit counter for transactions if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._autocommit

    @property
    def readConcern(self):
        """Extract readConcern Level if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._readConcern

    @property
    def w(self):
        """Extract write lock (w) counter if available (lazy)."""
        if not self._counters_calculated:
            self._counters_calculated = True
            self._extract_counters()

        return self._w

    def _extract_counters(self):
        """Extract counters like nscanned and nreturned from the logevent.

        Stored names stay on the legacy attributes. ``repaedtime`` is the
        historical typo that maps onto ``reapedtime``.
        """
        if self.logformat != LogFormat.LEGACY:
            return

        # extract counters (if present)
        counters = ['nscanned', 'nscannedObjects', 'ntoreturn', 'nreturned',
                    'ninserted', 'nupdated', 'ndeleted', 'r', 'w', 'numYields',
                    'planSummary', 'writeConflicts', 'keyUpdates', 'bytesRead',
                    'bytesWritten', 'timeReadingMicros', 'timeWritingMicros',
                    'lsid', 'txnNumber', 'autocommit', 'allowDiskUse', 'level',
                    'timeActiveMicros', 'timeInactiveMicros', 'duration',
                    'readTimestamp', 'terminationCause']

        # TODO: refactor mtools to use current counter names throughout
        # Transitionary hack: mapping of current names into prior equivalents.
        # That migration is not part of this parser: renaming the stored
        # attributes would change mloginfo output.
        counter_equiv = {
            'datetime': 'datetime',
            'docsExamined': 'nscannedObjects',
            'keysExamined': 'nscanned',
            'nDeleted': 'ndeleted',
            'nInserted': 'ninserted',
            'nMatched': 'nreturned',
            'nModified': 'nupdated',
            'cursorid': 'cursorid',
            'repaedtime': 'reapedtime'
        }
        counters.extend(counter_equiv.keys())

        # Tokens before operation. Both properties have side effects.
        split_tokens = self.split_tokens

        def same_token(token):
            return token.split(':')[-1].replace(',', '')

        def spaced_value(index):
            return split_tokens[index].replace(',', '')

        def store_spaced(counter, token, index):
            # pre-2.5.2 numYields with a space, for example "numYields: 2"
            # https://jira.mongodb.org/browse/SERVER-10101
            if counter == 'numYields' and token.startswith('numYields'):
                try:
                    self._numYields = int(spaced_value(index))
                except ValueError:
                    pass
            if counter == 'bytesRead' and token.startswith('bytesRead'):
                try:
                    self._bytesRead = int(spaced_value(index))
                except ValueError:
                    pass
            if counter == 'bytesWritten' and token.startswith('bytesWritten'):
                try:
                    self._bytesWritten = int(spaced_value(index))
                except ValueError:
                    pass
            if (counter == 'timeReadingMicros'
                    and token.startswith('timeReadingMicros')):
                try:
                    self._timeReadingMicros = int(spaced_value(index))
                except ValueError:
                    pass
            if (counter == 'timeWritingMicros'
                    and token.startswith('timeWritingMicros')):
                try:
                    self._timeWritingMicros = int(spaced_value(index))
                except ValueError:
                    pass
            # A non-numeric txnNumber still propagates.
            if counter == 'txnNumber' and token.startswith('txnNumber'):
                self._txnNumber = int(spaced_value(index))
            if counter == 'autocommit' and token.startswith('autocommit'):
                self._autocommit = spaced_value(index)
            # lsid's value is two tokens after the name, often "id:".
            if counter == 'lsid' and token.startswith('lsid'):
                self._lsid = split_tokens[index + 1].replace(',', '')
            if counter == 'planSummary' and token.startswith('planSummary'):
                try:
                    self._planSummary = split_tokens[index]
                    if self._planSummary:
                        if split_tokens[index + 1] != '{':
                            self._actualPlanSummary = self._planSummary
                        else:
                            self._actualPlanSummary = '%s %s' % (
                                self._planSummary,
                                self._find_pattern(
                                    'planSummary: %s' % self._planSummary,
                                    actual=True))
                except ValueError:
                    pass

        if self.operation:
            offset = self.datetime_nextpos + 2
            for t, token in enumerate(split_tokens[offset:]):
                for counter in counters:
                    if token.startswith('%s:' % counter):
                        try:
                            # Remap counter to standard name, if applicable.
                            # Special cases still match the original token.
                            counter = counter_equiv.get(counter, counter)
                            if counter == 'level' and token.startswith('level'):
                                self._readConcern = spaced_value(t + offset + 1)
                            elif (counter == 'readTimestamp'
                                  and token.startswith('readTimestamp')):
                                vars(self)['_' + counter] = same_token(token)
                            elif (counter == 'terminationCause'
                                  and token.startswith('terminationCause')):
                                vars(self)['_' + counter] = same_token(token)
                            else:
                                vars(self)['_' + counter] = int(same_token(token))

                            # allowDiskUse keeps the following token only after
                            # the same-token int() above succeeds. The second
                            # int() otherwise overwrites the value just stored.
                            if (counter == 'allowDiskUse'
                                    and token.startswith('allowDiskUse')):
                                self._allowDiskUse = spaced_value(t + offset + 1)
                            else:
                                vars(self)['_' + counter] = int(same_token(token))
                        except ValueError:
                            store_spaced(counter, token, t + offset + 1)

                        # The first matching counter name owns this token.
                        break

