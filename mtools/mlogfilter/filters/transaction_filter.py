import re

from .base_filter import BaseFilter

# SERVER-36461 - Filter to log slow transactions; Can be used in conjuncture with other filters


class TransactionFilter(BaseFilter):
    filterArgs = [
        ('--transactions', {
            'action': 'store_true', 'default': False,
            'help': 'only output lines containing logs of transactions'}),
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        # set the keyword as transaction if the --transaction flag is set
        if self.mlogfilter.args['transactions']:
            self.words = "transaction"
            self.active = True
        else:
            self.active = False

    def accept(self, logevent):
        """
        Process line.
        Overwrite BaseFilter.accept() and return True if the provided
        logevent contains keyword transaction, or False if not.
        """

        if re.search(self.words, logevent.line_str):
            return True
        else:
            return False
