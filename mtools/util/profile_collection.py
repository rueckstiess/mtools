from mtools.util.logevent import LogEvent
from mtools.util.input_source import InputSource
from dateutil.tz import tzutc
from pprint import pprint

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")

from pymongo import ASCENDING, DESCENDING

class ProfileCollection(InputSource):
    """ wrapper class for input source system.profile collection """

    datetime_format = "ISODate()"

    def __init__(self, hostname='localhost', port=27017, database='test', collection='system.profile'):
        """ constructor for ProfileCollection. Takes hostname, port, database and collection as parameters.
            All are optional and have default values.
        """

        # store parameters
        self.hostname = hostname
        self.port = port
        self.database = database
        self.collection = collection
        self.name = "%s.%s" % (database, collection)

        # property variables
        self._start = None
        self._end = None
        self._num_events = None

        self.cursor = None

        # test if database can be reached and collection exists
        try:
            mc = Connection(host=hostname, port=port)
            server_info = mc.server_info()
            self.versions = [ mc.server_info()[u'version'] ]
            binary = 'mongos' if mc.is_mongos else 'mongod'
            try:
                self.storage_engine = mc[database].command('serverStatus')[u'storageEngine'][u'name']
            except KeyError:
                self.storage_engine = 'mmapv1'

            self.binary = "%s (running on %s:%i)" % (binary, hostname, port)

        except (ConnectionFailure, AutoReconnect) as e:
            raise SystemExit("can't connect to database, please check if a mongod instance is running on %s:%s." % (hostname, port))

        self.coll_handle = mc[database][collection]

        if self.coll_handle.count() == 0:
            raise SystemExit("can't find any data in %s.%s collection. Please check database and collection name." % (database, collection))


    @property
    def start(self):
        """ lazy evaluation of start and end of events. """
        if not self._start:
            self._calculate_bounds()
        return self._start


    @property
    def end(self):
        """ lazy evaluation of start and end of events. """
        if not self._end:
            self._calculate_bounds()
        return self._end

    @property
    def num_events(self):
        """ lazy evaluation of the number of events. """
        if not self._num_events:
            self._num_events = self.coll_handle.count()
        return self._num_events


    def next(self):
        """ makes iterators. """
        if not self.cursor:
            self.cursor = self.coll_handle.find().sort([ ("ts", ASCENDING) ])

        doc = self.cursor.next()
        doc['thread'] = self.name
        le = LogEvent(doc)
        return le


    def __iter__(self):
        """ iteration over host object will return a LogEvent object for each document. """

        self.cursor = self.coll_handle.find().sort([ ("ts", ASCENDING) ])

        for doc in self.cursor:
            doc['thread'] = self.name
            le = LogEvent(doc)
            yield le


    def __len__(self):
        """ returns the number of events in the collection. """
        return self.num_events


    def _calculate_bounds(self):
        """ calculate beginning and end of log events. """

        # get start datetime
        first = self.coll_handle.find_one(None, sort=[ ("ts", ASCENDING) ])
        last = self.coll_handle.find_one(None, sort=[ ("ts", DESCENDING) ])

        self._start = first['ts']
        if self._start.tzinfo == None:
            self._start = self._start.replace(tzinfo=tzutc())

        self._end = last['ts']
        if self._end.tzinfo == None:
            self._end = self._end.replace(tzinfo=tzutc())

        return True


if __name__ == '__main__':
    pc = ProfileCollection()

    for event in pc:
        print(event)
