from bson import ObjectId
from mtools.util import OrderedDict

from random import choice, random, randint

from datetime import datetime
from dateutil import parser

import time
import string


class BaseOperator(object):
    names = []
    dict_format = False
    string_format = False
    defaults = OrderedDict()

    def __init__(self, decode_method):
        self._decode = decode_method


    def _parse_options(self, options={}):
        parsed = self.defaults.copy()

        if isinstance(options, list):
            parsed.update( zip(self.defaults.keys(), options) )

        elif isinstance(options, dict):
            parsed.update( options )

        for k,v in parsed.iteritems():
            if isinstance(v, unicode):
                parsed[k] = v.encode('utf-8')
        return parsed



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
        options = self._parse_options(options)

        # decode min and max first
        minval = self._decode(options['min'])
        maxval = self._decode(options['max'])
        assert minval <= maxval

        return randint(minval, maxval)



class FloatOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$float']
    defaults = OrderedDict([ ('min', 0.0), ('max', 1.0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max first
        minval = self._decode(options['min'])
        maxval = self._decode(options['max'])
        assert minval <= maxval

        val = random() * (maxval - minval) + minval
        return val



class IncOperator(BaseOperator):

    dict_format = False
    string_format = True
    names = ['$inc']
    value = -1

    def __call__(self, options=None):
        options = self._parse_options(options)

        self.value += 1
        return self.value


class StringOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$string', '$str']
    defaults = OrderedDict([ ('length', 10), ('mask', None) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max first
        length = self._decode(options['length'])
        mask = self._decode(options['mask'])

        if mask == None:
            mask = '.' * length

        assert length > 0
        result = ''.join( choice(string.ascii_letters + string.digits) for i in xrange(length) )

        return result


class MissingOperator(BaseOperator):

    dict_format = True
    string_format = True

    names = ['$missing']
    defaults = OrderedDict([ ('percent', 100), ('ifnot', None) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate percent
        percent = self._decode(options['percent'])

        if randint(1,100) <= percent:
            return '$missing'
        else:
            # ifnot is not yet evaluated, leave that up to another operator
            return options['ifnot']


class ChooseOperator(BaseOperator):

    dict_format = True
    names = ['$choose']
    defaults = OrderedDict([ ('from', []), ('weights', None) ])

    def __call__(self, options=None):
        # options can be arbitrary long list, store as "from" in options dictionary
        if isinstance(options, list):
            options = {'from': options}

        options = self._parse_options(options)

        # decode ratio
        weights = self._decode(options['weights'])
        if not weights:
            # pick one choice, uniformly distributed, but don't evaluate yet
            return choice(options['from'])
        else:
            assert len(weights) == len(options['from'])
            
            total_weight = 0
            acc_weight_items = []
            for item, weight in zip(options['from'], weights):
                total_weight += weight
                acc_weight_items.append( (total_weight, item) )
            
            pick = random() * total_weight
            for weight, item in acc_weight_items:
                if weight >= pick:
                    return item



class ArrayOperator(BaseOperator):

    dict_format = True
    names = ['$array']
    defaults = OrderedDict([ ('of', None), ('number', 10) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate number
        number = self._decode(options['number'])

        # build array of 'of' elements, but don't evaluate them yet
        return [ options['of'] ] * number


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

            td = dt - datetime.utcfromtimestamp(0)
            return int((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)
        else:
            return int(input)


    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode min and max and convert time formats to epochs
        mintime = self._parse_dt(self._decode(options['min']))
        maxtime = self._parse_dt(self._decode(options['max']))

        # generate random epoch number
        epoch = randint(mintime, maxtime)
        return datetime.fromtimestamp(epoch)


