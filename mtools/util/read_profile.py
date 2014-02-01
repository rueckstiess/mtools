from pymongo import MongoClient, ASCENDING
from mtools.util.logevent import LogEvent


mc = MongoClient()
database = 'test'
collection = 'profile_28'

for doc in mc[database][collection].find().sort([('ts', ASCENDING)]):

    # build a log line
    le = LogEvent('', auto_parse=False)

    le._thread = '<profile>'
    le._datetime = doc['ts']
    le._duration = doc['millis']
    le._operation = doc['op']
    le._namespace = doc['ns']
    if 'nscanned' in doc:
        le._nscanned = doc['nscanned']

    if 'numYield' in doc:
        le._numYields = doc['numYield']

    le._w = doc['lockStats']['timeLockedMicros']['w']
    le._r = doc['lockStats']['timeLockedMicros']['r']

    # all calculated
    le._split_tokens_calculated = True
    le._duration_calculated = True
    le._datetime_calculated = True
    le._thread_calculated = True
    le._operation_calculated = True
    le._counters_calculated = True

    locks = 'w:%i' % le.w if le.w else 'r:%i' % le.r
    duration = '%ims' % le.duration if le.duration else ''    

    payload = ''
    if 'query' in doc:
        payload += 'query: %s' % doc['query']
    if 'command' in doc:
        payload += 'command: %s' % doc['command']
    if 'updateobj' in doc:
        payload += ' update: %s' % doc['updateobj']

    scanned = 'nscanned:%i'%le._nscanned if 'nscanned' in doc else ''
    yields = 'numYields: %i'%le._numYields if 'numYield' in doc else ''


    le._line_str = "[{thread}] {operation} {namespace} {payload} {scanned} {yields} locks(micros) {locks} {duration}".format(
        datetime=le.datetime, thread=le.thread, operation=le.operation, namespace=le.namespace, payload=payload, scanned=scanned, yields=yields, locks=locks, duration=duration)

    le._reformat_timestamp("ctime", force=True)


    print ll