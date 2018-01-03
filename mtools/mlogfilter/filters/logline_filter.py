from .base_filter import BaseFilter
from mtools.util.logevent import LogEvent
from mtools.util.pattern import json2pattern


def custom_parse_array(value):
    return list(set(value.split()))


class LogLineFilter(BaseFilter):
    """LogLineFilter class."""

    filterArgs = [
        ('--component', {
            'nargs': '*',
            'action': 'store',
            'type': str.upper,
            'choices': LogEvent.log_components,
            'metavar': 'CM',
            'help': ('only output log lines with component CM '
                     '(multiple values are allowed).')
        }),
        ('--level', {
            'nargs': '*',
            'action': 'store',
            'metavar': 'LL',
            'choices': LogEvent.log_levels,
            'help': ('only output log lines with loglevel LL '
                     '(multiple values are allowed).')
        }),
        ('--namespace', {
            'nargs': '*',
            'action': 'store',
            'metavar': 'NS',
            'help': ('only output log lines on namespace NS '
                     '(multiple values are allowed).')
        }),
        ('--operation', {
            'nargs': '*',
            'action': 'store',
            'metavar': 'OP',
            'choices': LogEvent.log_operations,
            'help': ('only output log lines of type OP '
                     '(multiple values are allowed).')
        }),
        ('--thread', {
            'nargs': '*',
            'action': 'store',
            'help': ('only output log lines of thread THREAD '
                     '(multiple values are allowed).')
        }),
        ('--pattern', {
            'action': 'store',
            'help': ('only output log lines with a query pattern PATTERN '
                     '(only applies to queries, getmores, updates, removes).')
        }),
        ('--command', {
            'nargs': '*',
            'action': 'store',
            'help': ('only output log lines which are commands of the given '
                     'type. Examples: "distinct", "isMaster", '
                     '"replSetGetStatus" (multiple values are allowed).')
        }),
        ('--planSummary', {
            'nargs': '*',
            'action': 'store',
            'type': str.upper,
            'metavar': 'PS',
            'help': ('only output log lines which match the given plan '
                     'summary values (multiple values are allowed).')
            })
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        self.components = None
        self.levels = None
        self.namespaces = None
        self.operations = None
        self.threads = None
        self.commands = None
        self.pattern = None
        self.planSummaries = None

        if ('component' in self.mlogfilter.args and
                self.mlogfilter.args['component']):
            self.components = custom_parse_array(self.mlogfilter
                                                 .args['component'])
            self.active = True
        if 'level' in self.mlogfilter.args and self.mlogfilter.args['level']:
            self.levels = custom_parse_array(self.mlogfilter.args['level'])
            self.active = True
        if ('namespace' in self.mlogfilter.args and
                self.mlogfilter.args['namespace']):
            self.namespaces = custom_parse_array(self.mlogfilter
                                                 .args['namespace'])
            self.active = True
        if ('operation' in self.mlogfilter.args and
                self.mlogfilter.args['operation']):
            self.operations = custom_parse_array(self.mlogfilter
                                                 .args['operation'])
            self.active = True
        if ('command' in self.mlogfilter.args and
                self.mlogfilter.args['command']):
            self.commands = custom_parse_array(self.mlogfilter.args['command'])
            self.active = True
        if 'thread' in self.mlogfilter.args and self.mlogfilter.args['thread']:
            self.threads = custom_parse_array(self.mlogfilter.args['thread'])
            self.active = True
        if ('pattern' in self.mlogfilter.args and
                self.mlogfilter.args['pattern']):
            self.pattern = json2pattern(self.mlogfilter.args['pattern'])
            self.active = True
            if self.pattern is None:
                raise SystemExit("ERROR: cannot parse pattern \"%s\" as a JSON"
                                 " string" % self.mlogfilter.args['pattern'])
        if ('planSummary' in self.mlogfilter.args and
                self.mlogfilter.args['planSummary']):
            self.planSummaries = custom_parse_array(self.mlogfilter
                                                    .args['planSummary'])
            self.active = True

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        # if several filters are active, all have to agree
        if self.components and logevent.component not in self.components:
            return False
        if self.levels and logevent.level not in self.levels:
            return False
        if self.namespaces and logevent.namespace not in self.namespaces:
            return False
        if self.commands and logevent.command not in self.commands:
            return False
        if self.operations and logevent.operation not in self.operations:
            return False
        if self.threads:
            if (logevent.thread not in self.threads and
                    logevent.conn not in self.threads):
                return False
        if self.pattern and logevent.pattern != self.pattern:
            return False
        if (self.planSummaries and
                logevent.planSummary not in self.planSummaries):
            return False

        return True
