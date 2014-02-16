import re
import json

def _decode_pattern_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_pattern_list(item)
        elif isinstance(item, dict):
            item = _decode_pattern_dict(item)
        rv.append(item)

        rv = sorted(rv)
    return rv

def _decode_pattern_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
            if key in ['$in', '$gt', '$gte', '$lt', '$lte', '$exists']:
                return 1
            if key == '$nin':
                value = 1
            if key in ['query', '$query']:
                return _decode_pattern_dict(value)

        if isinstance(value, list):
            value = _decode_pattern_list(value)
        elif isinstance(value, dict):
            value = _decode_pattern_dict(value)
        else:
            value = 1

        rv[key] = value
    return rv


def json2pattern(s):
    """ converts JSON format (even mongo shell notation without quoted key names) to a query pattern """
    # make valid JSON by wrapping field names in quotes
    s, _ = re.subn(r'([{,])\s*([^,{\s\'"]+)\s*:', ' \\1 "\\2" : ' , s)
    # convert values to 1 where possible, to get rid of things like new Date(...)
    s, n = re.subn(r'([:,\[])\s*([^{}\[\]"]+?)\s*([,}\]])', '\\1 1 \\3', s)

    # now convert to dictionary, converting unicode to ascii 
    try:
        doc = json.loads(s, object_hook=_decode_pattern_dict)
        return json.dumps(doc, sort_keys=True, separators=(', ', ': ') )
    except ValueError:
        return None


if __name__ == '__main__':
    
    s = '{d: {$gt: 2, $lt: 4}, b: {$gte: 3}, c: {$nin: [1, "foo", "bar"]}, "$or": [{a:1}, {b:1}] }'
    print json2pattern(s)

    s = '{a: {$gt: 2, $lt: 4}, "b": {$nin: [1, 2, 3]}, "$or": [{a:1}, {b:1}] }'
    print json2pattern(s)

    s = '{ a: 1, b: { c: 2, d: "text" }, e: "more test" }'
    print json2pattern(s)

    s = '{ _id: ObjectId(\'528556616dde23324f233168\'), config: { _id: 2, host: "localhost:27017" }, ns: "local.oplog.rs" }'
    print json2pattern(s)
