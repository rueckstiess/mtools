from datetime import datetime
import re
from pymongo import Connection
from bson.min_key import MinKey

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



def presplit(host, database, collection, shardkey, disableBalancer=True):
    """ get information about the number of shards, then split chunks and distribute over shards. Currently assumes shardkey to be ObjectId/uuid (hex). """
    con = Connection(host)
    namespace = '%s.%s'%(database, collection)

    # enable sharding on database if not enabled yet
    db_info = con['config']['databases'].find_one({'_id':database})
    if not db_info or db_info['partitioned'] == False:
        con['admin'].command({'enableSharding': database})

    # shard collection
    coll_info = con['config']['collections'].find_one({'_id':namespace})
    if coll_info:
        print "collection already sharded."
        return
    else:
        con[database][collection].ensure_index(shardkey)
        con['admin'].command({'shardCollection': namespace, 'key': {shardkey:1}})

    # pre-split
    shards = list(con['config']['shards'].find())
    shard_names = [s['_id'] for s in shards]

    split_interval = 16 / len(shards)
    split_points = range(split_interval, len(shards)*split_interval, split_interval) 
    
    for s in split_points:
        # print {'split': namespace, 'middle': {shardkey: hex(s).lstrip('0x')} }
        con['admin'].command({'split': namespace, 'middle': {shardkey: hex(s).lstrip('0x')} })
    
    split_points = [MinKey] + split_points
    
    for i,s in enumerate(split_points):
        # print {'moveChunk': namespace, 'find': {shardkey: s}, 'to': shard_names[i] }
        con['admin'].command({'moveChunk': namespace, 'find': {shardkey: s, 'to': shard_names[i] }})


    # disable balancer
    con['config']['settings'].update({'_id':"balancer"}, {'$set':{'stopped': True}})


if __name__ == '__main__':
    presplit('capslock.local:27023', 'test', 'mycol', 'shardkey')

