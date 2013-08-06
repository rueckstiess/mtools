import re
from base_filter import BaseFilter


class WordFilter(BaseFilter):
    """ accepts only if line contains any of the words specified by --word 
    """

    filterArgs = [
        ('--word', {'action':'store', 'nargs':'*', 'help':'only output lines matching any of WORD'}),
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)

        # extract all arguments passed into 'word'
        if 'word' in self.commandLineArgs and self.commandLineArgs['word']:
            self.words = self.commandLineArgs['word'].split()
            self.active = True
        else:
            self.active = False

    def accept(self, logline):
        for word in self.words:
            if re.search(word, logline.line_str):
                return True
        return False
