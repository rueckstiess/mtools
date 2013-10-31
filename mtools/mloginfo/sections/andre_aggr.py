from datetime import date, time, datetime, timedelta, MINYEAR, MAXYEAR
import re
from collections import OrderedDict
from filters import DateTimeFilter

class NestedDict(OrderedDict):
	def __getitem__(self,key):
		if key in self: return self.get(key)
		return self.setdefault(key,NestedDict())

	def __repr__(self):
		result = []
		for key in self.keys():
			result.append('%s:%s' % (repr(key), repr(self[key])))
		return ''.join(['{', ', '.join(result), '}'])

class BaseAggregate:
	""" Base Aggregate, all other Aggregates inherit this class """

	filterArgs = []

	def __init__(self, commandLineArgs):
		""" constructor """
		self.commandLineArgs = commandLineArgs
		self.DateTimeFilter = DateTimeFilter(commandLineArgs)

		# set true individually
		self.active = False
	
	def accept(self, line):
		return False

	def addAggregateLine(self, aggregateObj, line):
		print "summary goes here"
	

class ConnexAggregate(BaseAggregate):
	""" For all "connection accepted" and "end connection" strings """
	filterArgs = [
		('--connex', { 'action' : 'store_true', 'default' : False, 'help' : 'output aggregate for connections'} ) 
	]
	
	def __init__(self, commandLineArgs):
		BaseAggregate.__init__(self, commandLineArgs)

		self.active = self.commandLineArgs['connex']
		self.aggregateObj = NestedDict()
		self.aggregateObj["NAME"] = { 'desc' : 'Aggregate information for connections' }
		self.aggregateObj["OPEN"] = { 'desc' : 'Total Connections Opened', 'count' : 0 }
		self.aggregateObj["CLOSED"] = { 'desc' : 'Total Connections Closed', 'count' : 0 }
		self.aggregateObj["ERRORS"] = { 'desc' : 'Total SocketExceptions', 'count' : 0 }

	def accept(self, line):
		if (self.DateTimeFilter.accept(line)) and (re.search('connection accepted', line) or re.search('end connection', line) or re.search("SocketException", line)):
			return True

	def addAggregateLine(self, line):
		
		tokens = line.split()
		if re.search('connection accepted', line):
			ip = tokens[8].split(':',1)[0]
			self.aggregateObj["OPEN"]["count"] +=1
			if self.aggregateObj[ip]["open"]["count"]:
				self.aggregateObj[ip]["open"]["count"] +=1
			else:
				self.aggregateObj[ip]["open"]["count"] = 1
			self.aggregateObj[ip]["open"]["desc"] = 'connections opened from '+ip
		if re.search('end connection', line):
			ip = tokens[7].split(':',1)[0]
			self.aggregateObj["CLOSED"]["count"] +=1
			if self.aggregateObj[ip]["closed"]["count"]:
				self.aggregateObj[ip]["closed"]["count"] +=1
			else:
				self.aggregateObj[ip]["closed"]["count"] =1
			self.aggregateObj[ip]["closed"]["desc"] = 'connections closed from '+ip
		if re.search("SocketException",line):
			self.aggregateObj["ERRORS"]["count"] += 1

class OpsAggregate(BaseAggregate):
	""" For all operations """
	filterArgs = [
		('--ops', { 'action' : 'store_true', 'default' : False, 'help' : 'output aggregate for connections' } ) 
	]

	def __init__(self, commandLineArgs):
		BaseAggregate.__init__(self, commandLineArgs)

		self.active = self.commandLineArgs['ops']
		self.aggregateObj = NestedDict()
		self.aggregateObj["NAME"] = { 'desc' : 'Aggregate information for operations' }
		self.aggregateObj["QUERY"] = { 'desc' : 'Total Queries', 'count' : 0, 'longest' : { "ms" : 0, "string" : ""} }
		self.aggregateObj["CMD"] = { 'desc' : 'Total Commands', 'count' : 0, 'longest' : { "ms" : 0, "string" : ""}}
		self.aggregateObj["UPDATE"] = { 'desc' : 'Total Updates', 'count' : 0, 'longest' : { "ms" : 0, "string" : ""} }
		self.aggregateObj["INSERT"] = { 'desc' : 'Total Inserts', 'count' : 0, 'longest' : { "ms" : 0, "string" : ""} }

	def accept(self, line):
		if (self.DateTimeFilter.accept(line)) and (re.search('[0-9]ms$', line)) and not (re.search('writebacklisten', line) or re.search("LockPing", line)):
			return	True

	def addAggregateLine(self, line):
		tokens = line.split()
		ms = long(tokens[-1][:-2])
		if('query' in tokens and 'update' not in tokens):
			self.aggregateObj["QUERY"]["count"] += 1
			if self.aggregateObj["QUERY"]["longest"]["ms"] < ms:
				self.aggregateObj["QUERY"]["longest"]["ms"] = ms
				self.aggregateObj["QUERY"]["longest"]["string"] = line
		if('update' in tokens):
			self.aggregateObj["UPDATE"]["count"] += 1
			if self.aggregateObj["UPDATE"]["longest"]["ms"] < ms:
				self.aggregateObj["UPDATE"]["longest"]["ms"] = ms
				self.aggregateObj["UPDATE"]["longest"]["string"] = line
		if('insert' in tokens):
			self.aggregateObj["INSERT"]["count"] +=1
			if self.aggregateObj["INSERT"]["longest"]["ms"] < ms:
				self.aggregateObj["INSERT"]["longest"]["ms"] = ms
				self.aggregateObj["INSERT"]["longest"]["string"] = line
		if('command' in tokens):
			self.aggregateObj["CMD"]["count"] +=1
			if self.aggregateObj["CMD"]["longest"]["ms"] < ms:
				self.aggregateObj["CMD"]["longest"]["ms"] = ms
				self.aggregateObj["CMD"]["longest"]["string"] = line
class SocketExceptionAggregate(BaseAggregate):
	""" for socket exceptions """

	filterArgs = [
		('--socketexp', { 'action' : 'store_true', 'default' : False, 'help' : 'output aggregate for socket exceptions'} ) 
	]

	def __init__(self, commandLineArgs):
		BaseAggregate.__init__(self, commandLineArgs)

		self.active = self.commandLineArgs['socketexp']
		self.aggregateObj = NestedDict()
		self.aggregateObj["NAME"] = { 'desc' : 'Aggregate information on socket exceptions'}

	def accept(self, line):
		if(self.DateTimeFilter.accept(line)) and re.search("SocketException", line):
			return True
	def addAggregateLine(self, line):
		tokens = line.split()
		etype = tokens[-3]
		if self.aggregateObj[etype]['count']:
			self.aggregateObj[etype]['count'] +=1
		else: self.aggregateObj[etype]['count'] = 1