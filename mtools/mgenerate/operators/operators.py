from bson import ObjectId
from mtools.util import OrderedDict

from random import choice
from random import randint

from datetime import datetime
from dateutil import parser

import time


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



class DateTimeOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$datetime', '$date']
    defaults = OrderedDict([ ('min', 0), ('max', int(time.time())) ])


    def _parse_dt(self, input):
        """ parse input, either int (epoch) or date string (use dateutil parser). """
        if isinstance(input, str):
            # string needs conversion, try parsing with dateutil's parser
            try:
                dt = parser.parse(input)
            except Exception as e:
                raise SystemExit("can't parse date/time format for %s." % input)

            return int(( dt - datetime.utcfromtimestamp(0) ).total_seconds())
        else:
            return int(input)


    def __call__(self, options=None):
        self._parse_options(options)

        # convert time formats to epochs
        mintime = self._parse_dt(self.options['min'])
        maxtime = self._parse_dt(self.options['max'])

        # generate random epoch number
        epoch = randint(mintime, maxtime)
        return datetime.fromtimestamp(epoch)


