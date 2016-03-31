from bson import ObjectId, Binary
from mtools.util import OrderedDict

from random import choice, random, randint, gauss
from numpy.random import zipf

from datetime import datetime
from dateutil import parser

import time
import string
import itertools
import calendar
import struct
import base64


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


class GaussOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$gauss', '$normal']
    defaults = OrderedDict([ ('mean', 0.0), ('std', 1.0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode mean and standard deviation
        mu = self._decode(options['mean'])
        sigma = self._decode(options['std'])

        val = gauss(mu, sigma)
        return val


class ZipfOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$zipf', '$zeta']
    defaults = OrderedDict([ ('alpha', 2.0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode distribution parameter
        alpha = self._decode(options['alpha'])

        val = zipf(alpha) - 1
        return val


class AgeOperator(GaussOperator):
    dict_format = False
    names = ['$age']

    def __call__(self, options=None):
        return int(GaussOperator.__call__(self, options=[36, 10]))


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

    dict_format = True
    string_format = True
    names = ['$inc']
    defaults = OrderedDict([ ('start', 0), ('step', 1) ])

    def __init__(self, decode_method):
        self.counter = None
        BaseOperator.__init__(self, decode_method)

    def __call__(self, options=None):
        options = self._parse_options(options)

        # initialize counter on first use (not threadsafe!)
        if self.counter == None:
            self.counter = itertools.count(options['start'], options['step'])

        return self.counter.next()

class PickOperator(BaseOperator):

    dict_format = True
    string_format = False
    names = ['$pick']
    defaults = OrderedDict([ ('array', []), ('element', 0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # decode choices and weights
        array = self._decode(options['array'])
        element = self._decode(options['element'])

        if len(array) <= element:
            return '$missing'

        return array[element]


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

        # decode choices and weights
        choices = options['from']
        weights = self._decode(options['weights'])
        if not weights:
            # pick one choice, uniformly distributed, but don't evaluate yet
            return choice(choices)
        else:
            assert len(weights) == len(choices)

            total_weight = 0
            acc_weight_items = []
            for item, weight in zip(choices, weights):
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


class ConcatOperator(BaseOperator):

    dict_format = True
    names = ['$concat']
    defaults = OrderedDict([ ('items', []), ('sep', '') ])

    def __call__(self, options=None):

        # options can be arbitrary long list, store as "items" in options dictionary
        if isinstance(options, list):
            options = {'items': options}

        options = self._parse_options(options)

        # evaluate items
        items = self._decode(options['items'])
        # separator
        sep = self._decode(options['sep'])

        # return concatenated string
        return sep.join(str(i) for i in items)


class CoordinateOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$coordinates', '$coordinate', '$coord', '$geo']
    defaults = OrderedDict([ ('long_lim', [-180, 180]), ('lat_lim', [-90, 90]) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate limits
        long_lim = self._decode(options['long_lim'])
        lat_lim = self._decode(options['lat_lim'])

        # return coordinate by using random numbers between limits
        return [ {"$float": long_lim }, {"$float": lat_lim }]


class PointOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$point']
    defaults = OrderedDict([ ('long_lim', [-180, 180]), ('lat_lim', [-90, 90]) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate limits
        long_lim = self._decode(options['long_lim'])
        lat_lim = self._decode(options['lat_lim'])

        # return coordinate by using random numbers between limits
        return { "type": "Point", "coordinates": { "$coord": [long_lim, lat_lim] } }


class BinaryOperator(BaseOperator):

    dict_format = True
    string_format = True
    names = ['$bin']
    defaults = OrderedDict([ ('length', 10), ('type', 0) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        # evaluate limits
        length = self._decode(options['length'])
        bintype = self._decode(options['type'])

        # return coordinate by using random numbers between limits
        assert length > 0
        bindata = ''.join( choice(string.ascii_letters + string.digits) for i in xrange(length) )

        return Binary(bindata, bintype)


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



class ObjectIdOperator(DateTimeOperator):
    """ with no parameters, just generate a new ObjectId. If min and/or max
        are provided, handle like DateTimeOperator and replace the timestamp
        portion in the ObjectId with the random date and time.
    """

    names = ['$objectid', '$oid']
    defaults = OrderedDict([ ('min', None), ('max', None) ])

    def __call__(self, options=None):
        options = self._parse_options(options)

        mintime = self._decode(options['min'])
        maxtime = self._decode(options['max'])

        if (mintime == None and maxtime == None):
            return ObjectId()

        # decode min and max and convert time formats to epochs
        mintime = self._parse_dt(mintime or 0)
        maxtime = self._parse_dt(maxtime or time.time())
        assert mintime <= maxtime

        # generate random epoch number
        epoch = randint(mintime, maxtime)
        oid = struct.pack(">i", int(epoch))+ ObjectId().binary[4:]

        return ObjectId(oid)
