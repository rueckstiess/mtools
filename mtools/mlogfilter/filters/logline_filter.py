from mtools.util.logline import LogLine
from base_filter import BaseFilter

class LogLineFilter(BaseFilter):
    """ 
    """
    filterArgs = [
        ('--namespace', {'action':'store', 'metavar':'NS', 'help':'only output log lines matching operations on NS.'}),
        ('--operation', {'action':'store', 'metavar':'OP', 'help':'only output log lines matching operations of type OP.'}),
        ('--thread',    {'action':'store', 'help':'only output log lines of thread THREAD.'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)

        self.namespace = None
        self.operation = None
        self.thread = None

        if 'namespace' in self.commandLineArgs and self.commandLineArgs['namespace']:
            self.namespace = self.commandLineArgs['namespace']
            self.active = True
        if 'operation' in self.commandLineArgs and self.commandLineArgs['operation']:
            self.operation = self.commandLineArgs['operation']
            self.active = True
        if 'thread' in self.commandLineArgs and self.commandLineArgs['thread']:
            self.thread = self.commandLineArgs['thread']
            self.active = True

    def accept(self, logline):
        if self.namespace and logline.namespace == self.namespace:
            return True
        if self.operation and logline.operation == self.operation:
            return True
        if self.thread and logline.thread == self.thread:
            return True

        return False
