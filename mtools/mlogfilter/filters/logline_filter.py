from mtools.util.logevent import LogEvent
from mtools.util.pattern import json2pattern
import re
from base_filter import BaseFilter

def custom_parse_array(value):
    return list(set(value.split()))

class LogLineFilter(BaseFilter):
    """ 
    """
    filterArgs = [
        ('--component', {
            'action':'store', 
            'nargs':'*', 
            'choices': ['-', 'ACCESS', 'COMMANDS', 'INDEXING', 'NETWORK', 'QUERY', 'REPLSETS', 
                       'SHARDING', 'STORAGE', 'JOURNAL', 'WRITES', 'S2', 'TOTAL'],
            'metavar':'CM', 
            'help':'only output log lines with component CM (multiple values are allowed).'
        }),
        ('--level',     {
            'action':'store', 
            'nargs':'*', 
            'metavar':'LL', 
            'choices': ['D', 'F', 'E', 'W', 'I', 'U'], 
            'help':'only output log lines  with loglevel LL (multiple values are allowed).'
        }),
        ('--namespace', {
            'action':'store', 
            'metavar':'NS', 
            'help':'only output log lines on namespace NS.'
        }),
        ('--operation', {
            'action':'store', 
            'metavar':'OP', 
            'choices': ['insert', 'update', 'remove', 'query', 'command', 'getmore'], 
            'help':'only output log lines of type OP.'
        }),
        ('--thread', {
            'action':'store', 
            'help':'only output log lines of thread THREAD.'
        }),
        ('--pattern', {
            'action':'store', 
            'help':'only output log lines that query with the pattern PATTERN' \
                   ' (only applies to queries, getmores, updates, removes)'
        })
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        self.components = None
        self.levels     = None
        self.namespace  = None
        self.operation  = None
        self.thread     = None
        self.pattern    = None

        if 'component' in self.mlogfilter.args and self.mlogfilter.args['component']:
            self.components = custom_parse_array(self.mlogfilter.args['component'])
            self.active = True
        if 'level' in self.mlogfilter.args and self.mlogfilter.args['level']:
            self.levels = custom_parse_array(self.mlogfilter.args['level'])
            self.active = True
        if 'namespace' in self.mlogfilter.args and self.mlogfilter.args['namespace']:
            self.namespace = self.mlogfilter.args['namespace']
            self.active = True
        if 'operation' in self.mlogfilter.args and self.mlogfilter.args['operation']:
            self.operation = self.mlogfilter.args['operation']
            self.active = True
        if 'thread' in self.mlogfilter.args and self.mlogfilter.args['thread']:
            self.thread = self.mlogfilter.args['thread']
            self.active = True
        if 'pattern' in self.mlogfilter.args and self.mlogfilter.args['pattern']:
            self.pattern = json2pattern(self.mlogfilter.args['pattern'])
            self.active = True

    def accept(self, logevent):
        # if several filters are active, all have to agree
        res = False
        if self.components and logevent.component not in self.components:
            return False
        if self.levels and logevent.level not in self.levels:
            return False
        if self.namespace and logevent.namespace != self.namespace:
            return False
        if self.operation and logevent.operation != self.operation:
            return False
        if self.thread:
            if logevent.thread != self.thread and logevent.conn != self.thread:
                return False
        if self.pattern and logevent.pattern != self.pattern:
            return False
        return True
