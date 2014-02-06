#!/usr/bin/env python

import json
import sys
import inspect 

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")


import mtools.mgenerate.operators as operators
from mtools.util.cmdlinetool import BaseCmdLineTool

class MGeneratorTool(BaseCmdLineTool):

    def __init__(self):
        BaseCmdLineTool.__init__(self)
        
        self.argparser.description = 'Script to generate pseudo-random data based on template documents.'
        
        self.argparser.add_argument('template', action='store', help='template for data generation, JSON or file')
        self.argparser.add_argument('--number', '-n', action='store', type=int, metavar='NUM', default=1, help='number of documents to insert.')
        self.argparser.add_argument('--host', action='store', default='localhost', help='mongod/s host to import data, default=localhost')
        self.argparser.add_argument('--port', action='store', default=27017, help='mongod/s port to import data, default=27017')
        self.argparser.add_argument('--database', '-d', action='store', metavar='D', default='test', help='database D to insert data, default=test')
        self.argparser.add_argument('--collection', '-c', action='store', metavar='C', default='mgendata', help='collection C to import data, default=mgendata')
        self.argparser.add_argument('--drop', action='store_true', default=False, help='drop collection before inserting data')
        self.argparser.add_argument('--stdout', action='store_true', default=False, help='prints data to stdout instead of inserting to mongod/s instance.')
        self.argparser.add_argument('--w', action='store', default=1, help='write concern for inserts, default=1')


        # add all operators classes from the operators module, pass in _decode method
        self.operators = [c[1](self._decode) for c in inspect.getmembers(operators, inspect.isclass)]
        
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


    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments)

        if self.args['template'].startswith('{'):
            # not a file
            try:
                template = json.loads(self.args['template'])
            except ValueError as e:
                raise SystemExit("can't parse template: %s" % e)
        else:
            try:
                f = open(self.args['template'])
            except IOError as e:
                raise SystemExit("can't open file %s: %s" % (self.args['template'], e))

            try:
                template = json.load(f)
            except ValueError as e:
                raise SystemExit("can't parse template in %s: %s" % (self.args['template'], e))


        if not self.args['stdout']:        
            mc = Connection(host=self.args['host'], port=self.args['port'], w=self.args['w'])        
            col = mc[self.args['database']][self.args['collection']]
            if self.args['drop']:
                col.drop()

        batch = []
        for n in xrange(self.args['number']):
            # decode the template
            doc = self._decode(template)

            if self.args['stdout']:
                print doc
            else:
                batch.append(doc)
                if n % 100 == 0:
                    col.insert(batch)
                    batch = []
                    self.update_progress(float(n) / self.args['number'], prefix='inserting data')

        if not self.args['stdout']:
            self.update_progress(1.0, prefix='inserting data')
            if batch:
                col.insert(batch)


    def _decode_operator(self, data):
        if isinstance(data, str):
            # string-format operator
            return self._decode(self.string_operators[data]())

        # dict-format operators should only ever have one key
        assert len(data.keys()) == 1
        key = data.keys()[0]
        value = data[key]
        # call operator with parameters (which will recursively evaluate sub-documents) and return result
        return self._decode(self.dict_operators[key](value))


    def _decode_list(self, data):
        rv = []
        for item in data:
            item = self._decode(item)
            if item != "$missing":
                rv.append(item)
        return rv


    def _decode_dict(self, data):
        rv = {}
        for key, value in data.iteritems():
            key = self._decode(key)
            value = self._decode(value)
            if value != "$missing":
                rv[key] = value
        return rv


    def _decode(self, data):

        # if dict, check if it's a dict-format command
        if isinstance(data, dict): 
            if data.keys()[0] in self.dict_operators:
                return self._decode_operator(data)
            else:
                return self._decode_dict(data)

        # decode as list
        if isinstance(data, list):
            return self._decode_list(data)

        # if it's a unicode string, encode as utf-8
        if isinstance(data, unicode):
            data = data.encode('utf-8')

        # decode string-format commands
        if isinstance(data, str) and data != "$missing" and data in self.string_operators:
            return self._decode_operator(data)

        # everything else, just return the data as is
        return data


if __name__ == '__main__':
    tool = MGeneratorTool()
    tool.run()