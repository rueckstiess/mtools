#!/usr/bin/env python3

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


def json2pattern(s, debug = False):
    """
    Convert JSON format to a query pattern.

    Includes even mongo shell notation without quoted key names.

    Pass debug = True to print additional info on each step of processing chain
    """
    saved_s = s

    if debug : print ("\n=======================\n", saved_s, file=sys.stderr)

    # make valid JSON by wrapping field names in quotes
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ', s)
    if debug : print (s, file=sys.stderr) 

    # handle shell values that are not valid JSON
    s = shell2json(s)
    if debug : print (s, file=sys.stderr)
    
    # convert to 1 where possible, to get rid of things like new Date(...)
    s, _ = re.subn(r'([:,\[])\s*([^{}\[\]"]+?)\s*([,}\]])', '\\1 1 \\3', s)
    if debug : print (s, file=sys.stderr)


    # replace list values by 1. Not the '$in/$nin' lists, but the like of: {..., "attrib" : ["val1", "val2", "3"],...}
    # updated regex, using positive lookahead and lookbehind to check for a " (quote) 
    # right after '['  and before ']' to correctly handle cases where a ']' is part of the value and 
    # also cases where list values are url's "nnn://aaa.bbb"  will correctly be simplified to '1'
    s, _ = re.subn(r'("\S+"\s*:\s*\[\s*(?=\"))(.+)((?<=\")\s*\]\s*[,}])', '\\1 1 \\3', s)

    if debug : print (s, file=sys.stderr)

    # now convert to dictionary, converting unicode to ascii
    doc = {}
    try:
        doc = json.loads(s, object_hook=_decode_pattern_dict)
    except Exception as err:
        if debug:
            ## print some context info and return without any extracted query data..
            msg = f'''json2pattern():json.loads Exception:\n  Error: {err} : {sys.exc_info()[0]}\n  saved_s: ({saved_s})\n  s: ({s})\n'''
            print(msg, file=sys.stderr)
        return None
    except:
        print (f'''json2pattern():json.loads Unexpected error: saved_s: ({saved_s}) sys.exc_info():{sys.exc_info()[0]}''' )
        raise


    try:
        return json.dumps(doc, sort_keys=True, separators=(', ', ': '), ensure_ascii=False)
    except Exception as err:
        ## print some context info and return without any extracted query data..
        if debug:
            msg = f'''json2pattern():json.dumps Exception:\n  Error: {sys.exc_info()[0]} : {err}\n  saved_s: ({saved_s})\n  doc: ({doc})\n'''
            print(msg, file=sys.stderr)
        return None
    except:
        print(f'''json2pattern():json.dumps Unexpected error: saved_s: ({saved_s}) sys.exc_info():{sys.exc_info()[0]}''')
        raise


if __name__ == '__main__':

    # define as True to get debug output of regex processing printed to stderr
    debug = False

    tests = { 
        '{d: {$gt: 2, $lt: 4}, b: {$gte: 3}, c: {$nin: [1, "foo", "bar"]}, "$or": [{a:"1uno"}, {b:"1uno"}] }'                : '{"$or": [{"a": 1}, {"b": 1}], "b": 1, "c": {"$nin": 1}, "d": 1}',
        '{a: {$gt: 2, $lt: 4}, "b": {$nin: [1, 2, 3]}, "$or": [{a:1}, {b:1}] }'                                              : '{"$or": [{"a": 1}, {"b": 1}], "a": 1, "b": {"$nin": 1}}', 
        "{a: {$gt: 2, $lt: 4}, b: {$in: [ ObjectId('1234564863acd10e5cbf5f6e'), ObjectId('1234564863acd10e5cbf5f7e') ] } }"  : '{"a": 1, "b": 1}', 
        "{ sk: -1182239108, _id: { $in: [ ObjectId('1234564863acd10e5cbf5f6e'), ObjectId('1234564863acd10e5cbf5f7e') ] } }"  : '{"_id": 1, "sk": 1}', 
        '{ a: 1, b: { c: 2, d: "text" }, e: "more test" }'                                                                   : '{"a": 1, "b": {"c": 1, "d": 1}, "e": 1}', 
        '{ _id: ObjectId(\'528556616dde23324f233168\'), config: { _id: 2, host: "localhost:27017" }, ns: "local.oplog.rs" }' : '{"_id": 1, "config": {"_id": 1, "host": 1}, "ns": 1}',

        # 20191231 - bugre - issue#764 - adding some more test cases.. based on our mongodb logs (mongod 4.0.3)
        r'{_id: ObjectId(\'528556616dde23324f233168\'), curList: [ "€", "XYZ", "Krown"], allowedSnacks: 1000 }'              : '{"_id": 1, "allowedSnacks": 1, "curList": [1]}', 
        r'{_id: "test", curList: [ "1onum]pas", "ab\]c" ] }'                                                                 : '{"_id": 1, "curList": [1]}',
        r'{ $and: [ { mode: ObjectId(\'5aafd085edb85e0dc09dd985\') }, { _id: { $ne: ObjectId(\'5e015519877718752d63dd9c\') } }, ' 
            '{ snack: { $in: [ "BLA", "RUN", "BLE" ] } }, { $or: [ { $and: [ { kind: "Solar" }, { wind: true }, '
            '{ beginTime: { $gte: new Date(1577134729858) } } ] }, { $and: [ { kind: "event" }, { endTime: { $gte: new Date(1577739529858) } } ] } ] } ] }'  : 
                '{"$and": [{"mode": 1}, {"_id": {"$ne": 1}}, {"snack": 1}, {"$or": [{"$and": [{"kind": 1}, {"wind": 1}, {"beginTime": 1}]}, {"$and": [{"kind": 1}, {"endTime": 1}]}]}]}',
        
        # @niccottrell use case and 2nd one extrapolating the 1st one. 
        r'{ urls: { $all: [ "https://surtronic.info/" ] } }'                      : '{"urls": {"$all": [1]}}',
        r'{ urls: { $all: [ "https://surtronic.info/", "http://url2.com" ] } }'   : '{"urls": {"$all": [1]}}'
    }

    for k,v in tests.items():
        r = json2pattern(k, debug)
        if ( r == v ):
            if debug :
                print(f'''OK...: {k}\n  Expect: {v}\n  Output: {r}\n\n''')
            else:
                print(f'''OK: {k}''')

        else:
            print(f'''\nERROR **: {k}\n  Expect: {v}\n  Output: {r}\n\n''')
