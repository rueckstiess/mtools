import re

from .base_filter import BaseFilter


class WordFilter(BaseFilter):
    """Accept only if line contains any of the words specified by --word."""

    filterArgs = [
        ('--word', {'action': 'store', 'nargs': '*',
                    'help': 'only output lines matching any of WORD'}),
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        # extract all arguments passed into 'word'
        if 'word' in self.mlogfilter.args and self.mlogfilter.args['word']:
            self.words = self.mlogfilter.args['word'].split()
            self.active = True
        else:
            self.active = False

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        for word in self.words:
            if re.search(word, logevent.line_str):
                return True
        return False
