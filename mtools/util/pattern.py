#!/usr/bin/env python3

import json
import re

import six


def _decode_pattern_list(data):
    rv = []
    contains_dict = False
    for item in data:
        if isinstance(item, six.text_type):
            item = item.encode('utf-8')
        elif isinstance(item, list):
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
    for key, value in six.iteritems(data):
        if isinstance(key, bytes):
            key = key.encode('utf-8')
        if isinstance(key, six.text_type):
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
    # make valid JSON by wrapping field names in quotes
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ', s)
    # handle shell values that are not valid JSON
    s = shell2json(s)
    # convert to 1 where possible, to get rid of things like new Date(...)
    s, n = re.subn(r'([:,\[])\s*([^{}\[\]"]+?)\s*([,}\]])', '\\1 1 \\3', s)
    # now convert to dictionary, converting unicode to ascii
    try:
        doc = json.loads(s, object_hook=_decode_pattern_dict)
        return json.dumps(doc, sort_keys=True, separators=(', ', ': '))
    except ValueError as ex:
        return None


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
