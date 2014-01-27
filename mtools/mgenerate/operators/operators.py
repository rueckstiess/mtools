from bson import ObjectId
from mtools.util import OrderedDict

from random import choice
from random import randint


class BaseOperator(object):
    names = []
    dict_format = False
    string_format = False
    late_eval = False
    defaults = OrderedDict()

    def _parse_options(self, options={}):
        self.options = self.defaults.copy()

        if isinstance(options, list):
            self.options.update( zip(self.defaults.keys(), options) )

        elif isinstance(options, dict):
            self.options.update( options )

        for k,v in self.options.iteritems():
            if isinstance(v, unicode):
                self.options[k] = v.encode('utf-8')


class ObjectIdOperator(BaseOperator):

    names = ['$objectid', '$oid']
    string_format = True

    def __call__(self, options=None):
        self._parse_options(options)
        return ObjectId()


class NumberOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$number', '$num']
    defaults = OrderedDict([ ('min', 0), ('max', 100) ])

    def __call__(self, options=None):
        self._parse_options(options)
        assert self.options['min'] <= self.options['max']
        return randint(self.options['min'], self.options['max'])


class MissingOperator(BaseOperator):

    dict_format = True
    string_format = True
    late_eval = True
    
    names = ['$missing']
    defaults = OrderedDict([ ('percent', 100), ('ifnot', None) ])

    def __call__(self, options=None):
        self._parse_options(options)

        if randint(1,100) <= self.options['percent']:
            return '$missing'
        else:
            return self.options['ifnot']


class ChooseOperator(BaseOperator):

    dict_format = True
    late_eval = True
    names = ['$choose']
    defaults = OrderedDict([ ('from', []) ])


    def __call__(self, options=None):
        # options can be arbitrary long list
        if isinstance(options, list):
            options = {'from': options}

        self._parse_options(options)

        return choice(self.options['from'])


class ArrayOperator(BaseOperator):

    dict_format = True
    names = ['$array']
    defaults = OrderedDict([ ('of', None), ('number', 10) ])


    def __call__(self, options=None):
        self._parse_options(options)

        return [ self.options['of'] ] * self.options['number']



