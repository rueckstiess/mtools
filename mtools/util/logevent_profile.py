#!/usr/bin/env python3
"""system.profile document parsing for LogEvent."""

import json

from dateutil.tz import tzutc


class ProfileParserMixin(object):
    """Copy a system.profile document onto a LogEvent."""

    def _parse_profile_doc(self, doc):
        """Parse system.profile doc, copy all values to member variables."""
        self._reset()

        self._split_tokens_calculated = True
        self._split_tokens = None

        self._duration_calculated = True
        self._duration = doc[u'millis']

        self._datetime_calculated = True
        self._datetime = doc[u'ts']
        if self._datetime.tzinfo is None:
            self._datetime = self._datetime.replace(tzinfo=tzutc())
        self._datetime_format = None
        self._reformat_timestamp('ctime', force=True)

        self._thread_calculated = True
        self._thread = doc['thread']

        self._operation_calculated = True
        self._operation = doc[u'op']
        self._namespace = doc[u'ns']

        self._command_calculated = True
        if self.operation == 'command':
            self._command = doc[u'command'].keys()[0]

        # query pattern for system.profile events, all three cases.
        # See SERVER-13245
        if 'query' in doc:
            if 'query' in doc['query'] and isinstance(doc['query']['query'],
                                                      dict):
                self._pattern = str(doc['query']['query']).replace("'", '"')
            elif '$query' in doc['query']:
                self._pattern = str(doc['query']['$query']).replace("'", '"')
            else:
                self._pattern = str(doc['query']).replace("'", '"')

            # sort pattern
            if ('orderby' in doc['query'] and
                    isinstance(doc['query']['orderby'], dict)):
                self._sort_pattern = str(doc['query']
                                         ['orderby']).replace("'", '"')
            elif '$orderby' in doc['query']:
                self._sort_pattern = str(doc['query']
                                         ['$orderby']).replace("'", '"')
            else:
                self._sort_pattern = None

        self._counters_calculated = True
        self._nscanned = doc[u'nscanned'] if 'nscanned' in doc else None
        self._ntoreturn = doc[u'ntoreturn'] if 'ntoreturn' in doc else None
        self._nupdated = doc[u'nupdated'] if 'nupdated' in doc else None
        self._nreturned = doc[u'nreturned'] if 'nreturned' in doc else None
        self._ninserted = doc[u'ninserted'] if 'ninserted' in doc else None
        self._ndeleted = doc[u'ndeleted'] if 'ndeleted' in doc else None
        self._numYields = doc[u'numYield'] if 'numYield' in doc else None
        self._txnNumber = doc[u'txnNumber'] if 'txnNumber' in doc else None
        self._lsid = doc[u'lsid'] if 'lsid' in doc else None
        self._autocommit = doc[u'autocommit'] if 'autocommit' in doc else None
        self._readConcern = doc[u'level'] if 'level' in doc else None
        self._timeActiveMicros = doc[u'timeActiveMicros'] if 'timeActiveMicros' in doc else None
        self._timeInactiveMicros = doc[u'timeInactiveMicros'] if 'timeInactiveMicros' in doc else None
        self._duration = doc[u'duration'] if 'duration' in doc else None
        self._datetime = doc[u'datetime'] if 'datetime' in doc else None

        if u'lockStats' in doc:
            self._r = doc[u'lockStats'][u'timeLockedMicros'][u'r']
            self._w = doc[u'lockStats'][u'timeLockedMicros'][u'w']
            self._r_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'r']
            self._w_acquiring = doc[u'lockStats']['timeAcquiringMicros'][u'w']
            locks = 'w:%i' % self.w if self.w is not None else 'r:%i' % self.r
        elif u'locks' in doc:
            locks = json.dumps(doc[u'locks'])
        else:
            locks = ''

        # build a fake line_str
        payload = ''
        if 'query' in doc:
            payload += ('query: %s' % str(doc[u'query'])
                        .replace("u'", "'").replace("'", '"'))
        if 'command' in doc:
            payload += ('command: %s' % str(doc[u'command'])
                        .replace("u'", "'").replace("'", '"'))
        if 'updateobj' in doc:
            payload += (' update: %s' % str(doc[u'updateobj'])
                        .replace("u'", "'").replace("'", '"'))

        scanned = 'nscanned:%i' % self._nscanned if 'nscanned' in doc else ''
        yields = 'numYields:%i' % self._numYields if 'numYield' in doc else ''
        duration = '%ims' % self.duration if self.duration is not None else ''

        # Imitate legacy log line format
        self._line_str = (f'''[{self.thread}] {self.operation} {self.namespace} {payload} '''
                          f'''{scanned} {yields} locks(micros) {locks} '''
                          f'''{duration}''')
