import json
import sys
from random import choice
from random import randint
from itertools import repeat

from mtools.util import OrderedDict
from bson import ObjectId


class BaseOperator(object):
    names = []
    dict_format = False
    string_format = False
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
    names = ['$choose']
    defaults = OrderedDict([ ('from', []) ])


    def __call__(self, options=None):
        # options can be arbitrary long list
        if isinstance(options, list):
            options = {'from': options}

        self._parse_options(options)

        return choice(self.options['from'])


# class DateDimeOperator(BaseOperator):

#     dict_format = True
#     string_format = True

#     names = ['$datetime', '$date']

#     defaults = OrderedDict([ ('min', 0), ('max', 100) ])

#     def __call__(self, options=None):
#         self._parse_options(options)
#         assert self.options['min'] <= self.options['max']
#         return randint(self.options['min'], self.options['max'])




class MGeneratorTool(object):

    operators = [ ObjectIdOperator(), NumberOperator(), MissingOperator(), ChooseOperator() ] 

    def __init__(self):
        
        self.string_operators = {}
        self.dict_operators = {}

        # separate into key and value operators
        for o in self.operators:
            if o.string_format:
                for name in o.names:
                    self.string_operators[name] = o
            if o.dict_format:
                for name in o.names:
                    self.dict_operators[name] = o


    def _construct_list(self, data, parent=None):
        rv = []
        for item in data:
            if isinstance(item, unicode):
                item = item.encode('utf-8')
                if item.startswith('$'):
                    item = self.string_operators[item]()
            
            if isinstance(item, list):
                item = self._construct_list(item)
            if isinstance(item, dict):
                item = self._construct_dict(item)
            rv.append(item)
        return rv


    def _construct_dict(self, data, parent=None):
        rv = {}
        return_key = False
        for key, value in data.iteritems():
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            if isinstance(value, unicode):
                value = value.encode('utf-8')

            if key.startswith('$') and key in self.dict_operators:
                return_key = True
                value = self.dict_operators[key](options=value)
                        
            if isinstance(value, list):
                value = self._construct_list(value)

            if isinstance(value, dict):
                value = self._construct_dict(value)

            if isinstance(value, str) and value.startswith('$') and value in self.string_operators:
                value = self.string_operators[value]()

            if return_key:
                return value

            # special case for missing value, has to be taken care of here
            if value != '$missing':
                rv[key] = value

        return rv



if len(sys.argv) > 1:
    dct = json.loads(sys.argv[1])
else:
    dct = json.load(open('example_doc.json', 'r'))


tool = MGeneratorTool()
result = tool._construct_dict(dct)
print result