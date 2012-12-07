#!/usr/bin/python

from bson import BSON
from pymongo import Connection
from itertools import chain

import time
import datetime
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


def insert_thread(thread_id, filename, n, namespace, batch=False, safe=False, uuid_shardkey=False, delay=None, verbose=False):
	# create connection to mongod
	con = Connection()

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
	total_time = time.time()
	batch_durs = []
	batch_sizes = []

	for i in xrange(n):
		if uuid_shardkey:
			packet = add_uuid_shardkey(packet)			

		if batch: 
			batch_time = time.time()

		con[database][collection].insert(packet, manipulate=False, safe=safe)
		
		if delay:
			time.sleep(delay)

		if batch:
			bd = time.time() - batch_time
			bs = len(packet)
			batch_durs.append(bd)
			batch_sizes.append(bs)
		
			if verbose:
				print 'thread_id %i    batchsize %i    duration %f    docs_per_sec %.2f'%(thread_id, bs, bd, bs/bd) 


	if rest > 0:
		if batch and uuid_shardkey:
			last_packet = add_uuid_shardkey(last_packet)
		
		if batch:
			batch_time = time.time()
		con[database][collection].insert(last_packet, manipulate=False, safe=safe)

		if delay: 
			time.sleep(delay)

		if batch:
			bd = time.time() - batch_time
			bs = len(last_packet)
			batch_durs.append(bd)
			batch_sizes.append(bs)

			if verbose:
				print 'thread_id %i    batchsize %i    duration %f    docs_per_sec %.2f'%(thread_id, bs, bd, bs/bd) 


	total_dur = time.time() - total_time
	
	return (total_dur, batch_durs, batch_sizes)


def run_test(args):
	# create db connection
	con = Connection(args['host'])
	
	db, coll = args['namespace'].split('.')

	# drop db if requested
	if not args['keep_db']:
		con.drop_database(db)

	if args['delay'] != None:
		args['delay'] /= 1000.

	if args['processes'] > multiprocessing.cpu_count():
		print "warning: more processes than cpus. reducing processes to %i"%multiprocessing.cpu_count()
		args['processes'] = multiprocessing.cpu_count()

	# create process pool
	pool = multiprocessing.Pool(args['processes'])

	# call function for each processor
	results = []
	for p in xrange(args['processes']-1):
		results.append(pool.apply_async(insert_thread, (p, args['jsonfile'], args['number']/args['processes'], \
			args['namespace'], args['batch'], args['safe'], args['uuid_shardkey'], args['delay'], args['verbose']) ))
	
	# insert the last batch of remaining documents
	results.append(pool.apply_async(insert_thread, (args['processes']-1, args['jsonfile'], args['number']/args['processes'] + args['number']%args['processes'], \
		args['namespace'], args['batch'], args['safe'], args['uuid_shardkey'], args['delay'], args['verbose']) ))

	pool.close()

	results = [r.get() for r in results]
	total_durs, batch_durs, batch_sizes = zip(*results)

	return (total_durs, batch_durs, batch_sizes) 


def interpret_results(args, total_durs, batch_durs, batch_sizes):
	results = {}

	# number of processes ran
	results['n_process'] = len(total_durs)

	# average total duration over all processes
	results['avg_process_dur'] = sum(total_durs) / results['n_process']

	# total docs per sec
	results['docs_per_sec'] = args['number'] / results['avg_process_dur']

	if args['batch']:
		batch_durs = list(chain(*batch_durs))
		batch_sizes = list(chain(*batch_sizes))

		batch_dps = [s/d for (d, s) in zip(batch_durs, batch_sizes)]

		# average duration per batch (over all batches in all processes)
		results['avg_batch_dur'] = sum(batch_durs) / len(batch_durs)
		results['avg_batch_dps'] = sum(batch_dps) / len(batch_dps)

	return results




if __name__ == '__main__':

	# create parser object
	parser = argparse.ArgumentParser(description='mongod/s load testing tool.')
	parser.add_argument('host', action='store', nargs='?', default='localhost:27017', help='HOST:PORT of mongos or mongod process')
	parser.add_argument('-p', '--processes', action='store', default=multiprocessing.cpu_count(), metavar='N', type=int, help='number of simultaneous processes (default = #cores')
	parser.add_argument('-b', '--batch', action='store', metavar='N', default=False, type=int, help='insert documents in batches of N')
	parser.add_argument('-n', '--number', action='store', metavar='N', default=10000, type=int, help='insert N documents total')
	parser.add_argument('-j', '--jsonfile', action='store', metavar='FILE', default='sample-small.json', help='filename for json document to insert')
	parser.add_argument('-s', '--safe', action='store_true', default=False, help='enable safe writes (w=1)')

	parser.add_argument('--delay', action='store', default=None, type=int, metavar='N', help='delay insertion per packet (batch/single doc) by N ms.')
	parser.add_argument('--namespace', action='store', default='test.minsert', metavar='NS', help='namespace (database.collection) to insert docs')
	parser.add_argument('--keep-db', action='store_true', default=False, help="keep old database, don't drop it before insertion")
	parser.add_argument('--uuid-shardkey', action='store_true', default=False, help='create random shard key for each document if enabled (default is ObjectId)')
	parser.add_argument('--verbose', action='store_true', default=False, help='print verbose information for each insert (only in batch mode)')

	args = vars(parser.parse_args())
	
	if args['verbose']:
		print "minsert.py test with parameters:"
		print
		for a in args:
			print "%15s: %s"%(a, args[a])
		print


	print "start timestamp:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	print

	total_durs, batch_durs, batch_sizes = run_test(args)
	results = interpret_results(args, total_durs, batch_durs, batch_sizes)

	# output result
	print
	print "     total time elapsed: %.2f sec (avg. over %i processes)"%(results['avg_process_dur'], results['n_process'])
	print "     total docs per sec: %.2f"%results['docs_per_sec']

	if args['batch']:
		print "        avg. batch time: %.4f sec"%results['avg_batch_dur']
		print "avg. batch docs per sec: %.4f sec"%results['avg_batch_dps']

	print
	print "end timestamp:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	






