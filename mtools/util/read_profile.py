from pymongo import MongoClient, ASCENDING
from mtools.util.logline import LogLine


mc = MongoClient()
database = 'test'
collection = 'profile_28'

for doc in mc[database][collection].find().sort([('ts', ASCENDING)]):

    # build a log line
    ll = LogLine('', auto_parse=False)

    ll._thread = '<profile>'
    ll._datetime = doc['ts']
    ll._duration = doc['millis']
    ll._operation = doc['op']
    ll._namespace = doc['ns']
    if 'nscanned' in doc:
        ll._nscanned = doc['nscanned']

    if 'numYield' in doc:
        ll._numYields = doc['numYield']

    ll._w = doc['lockStats']['timeLockedMicros']['w']
    ll._r = doc['lockStats']['timeLockedMicros']['r']

    # all calculated
    ll._split_tokens_calculated = True
    ll._duration_calculated = True
    ll._datetime_calculated = True
    ll._thread_calculated = True
    ll._operation_calculated = True
    ll._counters_calculated = True

    locks = 'w:%i' % ll.w if ll.w else 'r:%i' % ll.r
    duration = '%ims' % ll.duration if ll.duration else ''    

    payload = ''
    if 'query' in doc:
        payload += 'query: %s' % doc['query']
    if 'command' in doc:
        payload += 'command: %s' % doc['command']
    if 'updateobj' in doc:
        payload += ' update: %s' % doc['updateobj']

    scanned = 'nscanned:%i'%ll._nscanned if 'nscanned' in doc else ''
    yields = 'numYields: %i'%ll._numYields if 'numYield' in doc else ''


    ll._line_str = "[{thread}] {operation} {namespace} {payload} {scanned} {yields} locks(micros) {locks} {duration}".format(
        datetime=ll.datetime, thread=ll.thread, operation=ll.operation, namespace=ll.namespace, payload=payload, scanned=scanned, yields=yields, locks=locks, duration=duration)

    ll._reformat_timestamp("ctime", force=True)


    print ll