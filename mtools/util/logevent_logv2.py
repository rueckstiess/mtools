#!/usr/bin/env python3
"""Structured logv2 parsing for LogEvent."""

import sys

from mtools.util.pattern import json2pattern


class Logv2ParserMixin(object):
    """Parse a MongoDB 4.4+ structured log document."""

    def _parse_logv2(self, doc):
        """Parse logv2 format"""
        self._reset()

        self.counters_calculated = True

        self._datetime = self._match_datetime_pattern([doc['t']['$date']])
        self._datetime_calculated = True

        self._level = doc['s']  # Level aka severity
        self._component = doc['c']
        self._level_calculated = True

        # Thread name or execution context
        self._thread = doc['ctx']
        self._threadcalculated = True

        # operation: insert, update, remove, query, command, getmore, None
        # namespace: the namespace of the operation, or None
        # command: the type of command, if the operation was a "command"
        # pattern: the query pattern for queries, updates, counts, etc
        if 'attr' in doc:
            self._duration = doc['attr'].get('durationMillis')
            self._namespace = doc['attr'].get('ns')
            if self._namespace is None:
                # Some contexts use namespace instead of ns:
                #   initandlisten, LogicalSessionCacheRefresh,
                #   IndexBuildsCoordinatorMongod, ...
                self._namespace = doc['attr'].get('namespace')
            self._operation = doc['attr'].get('type')
            self._planSummary = doc['attr'].get('planSummary')
            self._queryHash = doc['attr'].get('queryHash')
            self._hasSortStage = doc['attr'].get('hasSortStage')
            self._numYields = doc['attr'].get('numYields')
            self._nscanned = doc['attr'].get('keysExamined')
            self._nscannedObjects = doc['attr'].get('docsExamined')
            self._ntoreturn = doc['attr'].get('ntoreturn')
            self._nupdated = doc['attr'].get('nModified')
            self._nreturned = doc['attr'].get('nReturned')
            if self._nreturned is None:
                # nReturned or nMatched (updates)
                self._nreturned = doc['attr'].get('nMatched')
            self._ninserted = doc['attr'].get('nInserted')
            self._ndeleted = doc['attr'].get('nDeleted')
            self._cursorid = doc['attr'].get('cursorid')
            self._app_name = doc['attr'].get('appName')
            # self._reapedtime  # TODO: https://jira.mongodb.org/browse/SERVER-28604

            if doc['attr'].get('type') == 'command':
                command = doc['attr']['command']

                if isinstance(command, dict):
                    try:
                        if command.get('filter'):
                            self._pattern = json2pattern(command['filter'], self._debug)
                        elif command.get('pipeline'):
                            self._pattern = json2pattern(command['pipeline'], self._debug)
                    except Exception as e:
                        if self._debug:
                            print(f"Exception: {e} for {doc}", file=sys.stderr)

                # The command name isn't explicitly listed but
                # should be the first element when an ordered
                # dict is iterated
                self._command = next(iter(command))

        self._operation_calculated = True
        self._duration_calculated = True
        self._command_calculated = True
        self._app_name_calculated = True
        self._split_tokens = None
        self._split_tokens_calculated = True
