from datetime import datetime
from pymongo import Connection
from pymongo.errors import OperationFailure
from bson.son import SON
import re
import time

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def extractDateTime(line):
    tokens = line.split()
    if len(tokens) < 4:
        # check if there are enough tokens for datetime
        return None

    # log file structure: Wed Sep 05 23:02:26 ...
    weekday, month, day, time = tokens[:4]
    
    # check if it is a valid datetime
    if not (weekday in weekdays and
    	    month in months and
            re.match(r'\d{1,2}', day) and
            re.match(r'\d{2}:\d{2}:\d{2}', time)):
        return None

    month = months.index(month)+1
    h, m, s = time.split(':')

    # TODO: special case if year rolls over but logfile is from old year
    year = datetime.now().year

    dt = datetime(int(year), int(month), int(day), int(h), int(m), int(s))

    return dt



def presplit(host, database, collection, shardkey):
    """ get information about the number of shards, then split chunks and 
        distribute over shards. Currently assumes shardkey to be hex string,
        for example ObjectId or UUID. 
    """
    
    con = Connection(host)
    namespace = '%s.%s'%(database, collection)

    # disable balancer
    con['config']['settings'].update({'_id':"balancer"}, {'$set':{'stopped': True}}, upsert=True)

    # enable sharding on database if not yet enabled
    db_info = con['config']['databases'].find_one({'_id':database})
    if not db_info or db_info['partitioned'] == False:
        con['admin'].command(SON({'enableSharding': database}))

    # shard collection if not yet sharded
    coll_info = con['config']['collections'].find_one({'_id':namespace})
    if coll_info and not coll_info['dropped']:
        # if it is sharded already, quit. something is not right.
        print "collection already sharded."
        return
    else:
        con[database][collection].ensure_index(shardkey)
        con['admin'].command(SON({'shardCollection': namespace, 'key': {shardkey:1}}))

    # get shard number and names and calculate split points
    shards = list(con['config']['shards'].find())

    if len(shards) == 1:
        print "only one shard found. no pre-splitting required."
        return

    shard_names = [s['_id'] for s in shards]
    split_interval = 16 / len(shards)
    split_points = [hex(s).lstrip('0x') for s in range(split_interval, len(shards)*split_interval, split_interval)]
    
    # pre-splitting commands
    for s in split_points:
        con['admin'].command(SON([('split',namespace), ('middle', {shardkey: s})]))
    
    split_points = ['MinKey'] + split_points

    # move chunks to shards (catch the one error where the chunk resides on that shard already)
    for i,s in enumerate(split_points):
        try:
            print [('moveChunk',namespace), ('find', {shardkey: s}), ('to', shard_names[i])]
            res = con['admin'].command(SON([('moveChunk',namespace), ('find', {shardkey: s}), ('to', shard_names[i])]))
            print res
        except OperationFailure, e:
            print e


if __name__ == '__main__':
    # test presplitting function
    presplit('capslock.local:27024', 'test', 'mycol', 'my_id')

