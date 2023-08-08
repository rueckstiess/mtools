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

def values2pattern(x, debug = False):
    """Recursively convert values to placeholder patterns"""
    if isinstance(x, list):
        return [values2pattern(v) for v in x]
    elif isinstance(x, dict):
        return {k: values2pattern(v) for k, v in x.items()}
    else:
        return 1


def add_double_quotes_to_key(s):
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ', s)
    return s

def json2pattern(s, debug = False):
    """
    Convert JSON format to a query pattern.

    Includes even mongo shell notation without quoted key names.

    Pass debug = True to print additional info on each step of processing chain
    """
    doc = None
    if (isinstance(s, dict)):
        if debug : print ("\n=== json2pattern() from dict\n", s, file=sys.stderr)
        doc = values2pattern(s)

    elif (isinstance(s, list)):
        if debug : print ("\n=== json2pattern() from list\n", s, file=sys.stderr)
        doc = values2pattern(s)

    elif isinstance(s, str):
        # Given a JSON-like string (eg legacy logs, mangle into something JSONish)
        saved_s = s

        if debug : print ("\n=== json2pattern() from legacy string\n", saved_s, file=sys.stderr)

        s = add_double_quotes_to_key(s)
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
        try:
            doc = json.loads(s, object_hook=_decode_pattern_dict)
        except Exception as err:
            if debug:
                ## print some context info and return without any extracted query data..
                msg = f'''json2pattern():json.loads Exception:\n  Error: {err} : {sys.exc_info()[0]}\n s: ({s})\n'''
                print(msg, file=sys.stderr)
            return None
        except:
            print (f'''json2pattern():json.loads Unexpected error: s: ({s}) sys.exc_info():{sys.exc_info()[0]}''' )
            raise
    else:
        print (f'''json2pattern(): Unsupported parameter type: {type(s)}''')
        return

    try:
        return json.dumps(doc, sort_keys=True, separators=(', ', ': '), ensure_ascii=False)
    except Exception as err:
        ## print some context info and return without any extracted query data..
        if debug:
            msg = f'''json2pattern():json.dumps Exception:\n  Error: {sys.exc_info()[0]} : {err}\n  s: ({s})\n  doc: ({doc})\n'''
            print(msg, file=sys.stderr)
        return None
    except:
        print(f'''json2pattern():json.dumps Unexpected error: s: ({s}) sys.exc_info():{sys.exc_info()[0]}''')
        raise
