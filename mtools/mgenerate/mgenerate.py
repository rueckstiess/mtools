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
        self.argparser.add_argument('--out', action='store_true', default=False, help='prints data to stdout instead of inserting to mongod/s instance.')
        self.argparser.add_argument('-w', action='store', default=1, help='write concern for inserts, default=1')


        # add all filter classes from the filters module
        self.operators = [c[1]() for c in inspect.getmembers(operators, inspect.isclass)]
        
        self.string_operators = {}
        self.dict_operators = {}
        self.late_operators = {}

        # separate into key and value operators
        for o in self.operators:
            if o.string_format:
                for name in o.names:
                    self.string_operators[name] = o
            if o.dict_format:
                for name in o.names:
                    self.dict_operators[name] = o
                    if o.late_eval:
                        self.late_operators[name] = o


    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments)

        if self.args['template'].startswith('{'):
            # not a file
            try:
                template = json.loads(self.args['template'], object_hook=self._decode_dict)
            except ValueError as e:
                raise SystemExit("can't parse template: %s" % e)
        else:
            try:
                f = open(self.args['template'])
            except IOError as e:
                raise SystemExit("can't open file %s: %s" % (self.args['template'], e))

            try:
                template = json.load(f, object_hook=self._decode_dict)
            except ValueError as e:
                raise SystemExit("can't parse template in %s: %s" % (self.args['template'], e))


        if not self.args['out']:        
            mc = Connection(host=self.args['host'], port=self.args['port'], w=self.args['w'])        
            col = mc[self.args['database']][self.args['collection']]
            if self.args['drop']:
                col.drop()

        batch = []
        for n in xrange(self.args['number']):
            # two evaluation rounds, early and late
            doc = self._construct_dict(template, late=False)
            doc = self._construct_dict(doc, late=True)

            if self.args['out']:
                print doc
            else:
                batch.append(doc)
                if n % 100 == 0:
                    col.insert(batch)
                    batch = []
                    self.update_progress(float(n) / self.args['number'], prefix='inserting data')

        if not self.args['out']:
            self.update_progress(1.0, prefix='inserting data')
            if batch:
                col.insert(batch)


    def _decode_list(self, data):
        rv = []
        for item in data:
            if isinstance(item, unicode):
                item = item.encode('utf-8')
            elif isinstance(item, list):
                item = self._decode_list(item)
            elif isinstance(item, dict):
                item = self._decode_dict(item)
            rv.append(item)
        return rv


    def _decode_dict(self, data):
        rv = {}
        for key, value in data.iteritems():
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            elif isinstance(value, list):
                value = self._decode_list(value)
            elif isinstance(value, dict):
                value = self._decode_dict(value)
            rv[key] = value
        return rv


    def _construct_list(self, data, late=False):
        rv = []
        for item in data: 
            
            if not late:
                # skip late evaluations in the first round (like $choose)
                if isinstance(item, str) and item.startswith('$') and item in self.late_operators:
                    rv.append(item)
                    continue
           
            if isinstance(item, list):
                item = self._construct_list(item, late=late)

            if isinstance(item, dict):
                item = self._construct_dict(item, True)

            if isinstance(item, str) and item.startswith('$'):
                item = self.string_operators[item]()

            if item != '$missing':
                rv.append(item)

        return rv


    def _construct_dict(self, data, late=False):
        rv = {}
        for key, value in data.iteritems():                        

            if not late:
                # skip late evaluations in the first round (like $choose)
                if key.startswith('$') and key in self.late_operators:
                    rv[key] = value
                    continue

            if isinstance(value, dict):
                value = self._construct_dict(value, late=late)

            if isinstance(value, list):
                value = self._construct_list(value)

            if isinstance(value, str) and value.startswith('$') and value in self.string_operators:
                value = self.string_operators[value]()

            if key.startswith('$') and key in self.dict_operators:
                return self.dict_operators[key](options=value)

            # special case for missing value, has to be taken care of here
            if value != '$missing':
                rv[key] = value

        return rv


if __name__ == '__main__':
    tool = MGeneratorTool()
    tool.run()