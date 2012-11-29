from bson import BSON
from pymongo import Connection
import time
import multiprocessing
import argparse
import uuid
import types


def add_uuid_shardkey(packet):
	""" take a packet (either list of docs, or doc) and add random uuid strings as _id. """
	if type(packet) != types.ListType:
		packet['_id'] = uuid.uuid4().hex
	else:
		for i,p in enumerate(packet):
			packet[i]['_id'] = uuid.uuid4().hex
	
	return packet


def insert_thread(filename, n, namespace, batch=False, safe=False, uuid_shardkey=False, delay=None):
	# create connection to mongod
	con = Connection()

	verbose = True

	# load document
	f = open(filename, 'r')
	doc = eval(f.read())
	f.close()

	database, collection = namespace.split('.')

	if batch:
		# calculate new number of insertions with batch packets
		rest = n % batch
		if rest > 0:
			last_packet = [doc.copy() for _ in xrange(rest)]
		packet = [doc.copy() for _ in xrange(batch)]
		n = n / batch
	else: 
		rest = 0
		packet = doc

	# start execution loop
	t = time.time()

	for i in xrange(n):
		if uuid_shardkey:
			packet = add_uuid_shardkey(packet)			

		if verbose:
			print packet
		con[database][collection].insert(packet, manipulate=False, safe=safe)
		if delay:
			time.sleep(delay)

	if rest > 0:
		if batch and uuid_shardkey:
			last_packet = add_uuid_shardkey(last_packet)
		
		if verbose:
			print last_packet
		con[database][collection].insert(last_packet, manipulate=False, safe=safe)
		if delay: 
			time.sleep(delay)

	dur = time.time() - t
	return dur


def run_test(args):
	# create db connection
	con = Connection(args['host'])
	
	db, coll = args['namespace'].split('.')

	# drop db if requested
	if not args['keep_db']:
		con.drop_database(db)

	# create process pool
	pool = multiprocessing.Pool(args['processes'])

	# call function for each processor
	results = []
	for p in xrange(args['processes']-1):
		results.append(pool.apply(insert_thread, (args['jsonfile'], args['number']/args['processes'], \
			args['namespace'], args['batch'], args['safe'], args['uuid_shardkey']) ))
	
	# insert the last batch of remaining documents
	results.append(pool.apply(insert_thread, (args['jsonfile'], args['number']/args['processes'] + args['number']%args['processes'], \
		args['namespace'], args['batch'], args['safe'], args['uuid_shardkey'], args['delay']/1000.) ))

	pool.close()
	pool.join()

	sum_res = sum(results)
	dps_res = sum_res / len(results)

	return (sum_res, dps_res) 


if __name__ == '__main__':

	# create parser object
	parser = argparse.ArgumentParser(description='mongod/s load testing tool.')
	parser.add_argument('host', action='store', nargs='?', default='localhost:27017', help='HOST:PORT of mongos or mongod process')
	parser.add_argument('-p', '--processes', action='store', default=1, metavar='N', type=int, help='number of simultaneous processes')
	parser.add_argument('-b', '--batch', action='store', metavar='N', default=False, type=int, help='insert documents in batches of N')
	parser.add_argument('-n', '--number', action='store', metavar='N', default=10000, type=int, help='insert N documents total')
	parser.add_argument('-j', '--jsonfile', action='store', metavar='FILE', default='sample-small.json', help='filename for json document to insert')
	parser.add_argument('-s', '--safe', action='store_true', default=False, help='enable safe writes (w=1)')

	parser.add_argument('--delay', action='store', default=None, type=int, metavar='N', help='delay insertion per packet (batch/single doc) by N ms.')
	parser.add_argument('--namespace', action='store', default='test.minsert', metavar='NS', help='namespace (database.collection) to insert docs')
	parser.add_argument('--keep-db', action='store_true', default=False, help="keep old database, don't drop it before insertion")
	parser.add_argument('--uuid-shardkey', action='store_true', default=False, help='create random shard key for each document if enabled (default is ObjectId)')
	
	args = vars(parser.parse_args())

	sum_res, dps_res = run_test(args)

	# output result
	print sum_res, dps_res
