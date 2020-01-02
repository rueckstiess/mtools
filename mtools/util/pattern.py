#!/bin/python

import json
import re

import sys


def _decode_pattern_list(data):
    rv = []
    contains_dict = False
    for item in data:
        if isinstance(item, list):
            item = _decode_pattern_list(item)
        elif isinstance(item, dict):
            item = _decode_pattern_dict(item)
            contains_dict = True
        rv.append(item)

    # avoid sorting if any element in the list is a dict
    if not contains_dict:
        rv = sorted(rv)

    return rv


def _decode_pattern_dict(data):
    rv = {}
    for key, value in data.items():
        if isinstance(key, bytes):
            key = key.encode('utf-8')
        if isinstance(key, str):
            if key in ['$in', '$gt', '$gte', '$lt', '$lte', '$exists']:
                return 1
            if key == '$nin':
                value = 1
            if key in ['query', '$query']:
                try:
                    # Try to decode value as a dictionary; this will fail if
                    # there happens to be a field called "query"
                    return _decode_pattern_dict(value)
                except:
                    return value

        if isinstance(value, list):
            value = _decode_pattern_list(value)
        elif isinstance(value, dict):
            value = _decode_pattern_dict(value)
        else:
            value = 1
        rv[key] = value
    return rv


def shell2json(s):
    """Convert shell syntax to json."""
    replace = {
        r'BinData\(.+?\)': '1',
        r'(new )?Date\(.+?\)': '1',
        r'Timestamp\(.+?\)': '1',
        r'ObjectId\(.+?\)': '1',
        r'DBRef\(.+?\)': '1',
        r'undefined': '1',
        r'MinKey': '1',
        r'MaxKey': '1',
        r'NumberLong\(.+?\)': '1',
        r'/.+?/\w*': '1'
    }

    for key, value in replace.items():
        s = re.sub(key, value, s)

    return s


def json2pattern(s):
    """
    Convert JSON format to a query pattern.

    Includes even mongo shell notation without quoted key names.
    """
    saved_s = s
    # make valid JSON by wrapping field names in quotes
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ', s)
    # handle shell values that are not valid JSON
    s = shell2json(s)
    # convert to 1 where possible, to get rid of things like new Date(...)
    s, n = re.subn(r'([:,\[])\s*([^{}\[\]"]+?)\s*([,}\]])', '\\1 1 \\3', s)
    # now convert to dictionary, converting unicode to ascii
    doc = {}
    try:
        doc = json.loads(s, object_hook=_decode_pattern_dict)
    except Exception as err:
        ## print some context info and return without any extracted query data..
        print ("json2pattern():json.loads Exception:\n  Error: {1} : {0}\n  saved_s: ({2})\n  s: ({3})\n".
            format(err, sys.exc_info()[0], saved_s, s), file=sys.stderr)
        return None
    except:
        print ("json2pattern():json.loads Unexpected error: save_s: ({0}) sys.exc_info():{1}".format(saved_s, sys.exc_info()[0]) )
        raise


    try:
        return json.dumps(doc, sort_keys=True, separators=(', ', ': '), ensure_ascii=False)
    except Exception as err:
        ## print some context info and return without any extracted query data..
        print ("json2pattern():json.dumps Exception:\n  Error: {1} : {0}\n  saved_s: ({2})\n  doc: ({3})\n".
            format(err, sys.exc_info()[0], saved_s, doc), file=sys.stderr)
        return None
    except:
        print ("json2pattern():json.dumps Unexpected error: save_s: ({0}) sys.exc_info():{1}".format(saved_s, sys.exc_info()[0]) )
        raise


if __name__ == '__main__':

    s = ('{d: {$gt: 2, $lt: 4}, b: {$gte: 3}, '
         'c: {$nin: [1, "foo", "bar"]}, "$or": [{a:1}, {b:1}] }')
    print(json2pattern(s))

    s = ('{a: {$gt: 2, $lt: 4}, '
         '"b": {$nin: [1, 2, 3]}, "$or": [{a:1}, {b:1}] }')
    print(json2pattern(s))

    s = ('{a: {$gt: 2, $lt: 4}, '
         '"b": {$nin: [1, 2, 3]}, "$or": [{a:1}, {b:1}] }')
    print(json2pattern(s))

    s = ("{a: {$gt: 2, $lt: 4}, "
         "b: {$in: [ ObjectId('1234564863acd10e5cbf5f6e'), "
         "ObjectId('1234564863acd10e5cbf5f7e') ] } }")
    print(json2pattern(s))

    s = ("{ sk: -1182239108, "
         "_id: { $in: [ ObjectId('1234564863acd10e5cbf5f6e'), "
         "ObjectId('1234564863acd10e5cbf5f7e') ] } }")
    print(json2pattern(s))

    s = '{ a: 1, b: { c: 2, d: "text" }, e: "more test" }'
    print(json2pattern(s))

    s = ('{ _id: ObjectId(\'528556616dde23324f233168\'), '
         'config: { _id: 2, host: "localhost:27017" }, ns: "local.oplog.rs" }')
    print(json2pattern(s))

    ##
    ## 20191231 - bugre - issue#764 - adding some more test cases.. based on our mongodb logs (mongod 4.0.3)
    ##
    s = (r'{_id: ObjectId(\'528556616dde23324f233168\'), curList: [ "€", "XYZ", "Krown"], allowedSnacks: 1000 }')
    print(json2pattern(s))
