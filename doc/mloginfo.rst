.. _mloginfo:

========
mloginfo
========

**mloginfo** takes a log file and reports :ref:`default-info` about the
log file. The script also has some options for additional :ref:`info-sections`.


Usage
~~~~~

.. code-block:: bash

   mloginfo [-h] logfile
            [--clients]
            [--connections]
            [--cursors]
            [--distinct]
            [--queries]
               [--rounding {0,1,2,3,4}]
               [--sort {namespace,pattern,count,min,max,mean,95%,sum}]
            [--restarts]
            [--rsstate]
            [--storagestats]
            [--transactions]
               [--tsort {duration}]
            [--verbose]
            [--version]

General Parameters
~~~~~~~~~~~~~~~~~~

Help
----
``-h, --help``
   shows the help text and exits.

Version
-------
``--version``
   shows the version number and exits.

Verbosity
---------
``--verbose``
   shows extra information, depending on the different sections.

.. _default-info:

Default Information
~~~~~~~~~~~~~~~~~~~

By default, **mloginfo** will output general information about the log file,
including start and end of the file and the number of lines. If a restart was
found in the file, it will also output the binary (``mongod`` or ``mongos``)
and the version history.

Example:

.. code-block:: bash

   mloginfo mongod.log

        source: mongod.log
          host: enter.local:27019
         start: 2017 Dec 14 05:56:48.578
           end: 2017 Dec 14 05:57:55.965
   date format: iso8601-local
        length: 190
        binary: mongod
       version: 3.4.9
       storage: wiredTiger

.. _info-sections:

Sections
~~~~~~~~

In addition to the general information, **mloginfo** also supports different
information sections, that can be invoked with an additional parameter.
Depending on the section, gathering the information may take some time. The
sections are described below.

Queries (``--queries``)
-----------------------

The queries section will go through the log file and find all queries
(including queries from updates) and collect some statistics for each query
pattern. A query pattern is the shape or signature of a query (similar to an
index definition) without the actual query values for each field.

The section shows a table with namespace (in usual database.collection syntax),
the query pattern, and various statistics, like how often this query pattern
was found (count), the minimum and maximum execution time, the mean and the
total sum. It also informs the type of operation that was performed. The list
is sorted by total sum, which reflects the overall work the database has to
perform for each query pattern. The ``allowDiskUsage`` (last column) parameter
provides information about the disk usage of a namespace. The slow query log
entry shows a value of "True" or "False" if the disk was used, or "None" if
this information is not available in the log.

This overview is very useful to know which indexes to create to get the best
performance out of a MongoDB environment. Optimization efforts should start at
the top of the list and work downwards, to get the highest overall improvement
with the least amount of index creation.

For example:

.. code-block:: bash

   mloginfo mongod.log --queries

In addition to the default information, this command will also output the
``QUERIES`` section:

.. code-block:: bash

   QUERIES

   namespace                  operations    pattern                                        count    min (ms)    max (ms)    mean (ms)       95%-ile (ms)    sum (ms)        allowDiskUse

   serverside.scrum_master    update        {"datetime_used": {"$ne": 1}}                     20       15753       17083        16434          1.8          328692          True
   serverside.django_session  find          {"_id": 1}                                       562         101        1512          317          2.0          178168          False
   serverside.user            find          {"_types": 1, "emails.email": 1}                 804         101        1262          201          1.0          162311          False
   local.slaves               find          {"_id": 1, "host": 1, "ns": 1}                   131         101        1048          310          0.0          40738           True
   serverside.email_alerts    update        {"_types": 1, "email": 1, "pp_user_id": 1}        13         153       11639         2465          0.0          32053           None
   serverside.sign_up         update        {"_id": 1}                                        77         103         843          269          1.8          20761           None
   serverside.user_credits    remove        {"_id": 1}                                         6         204         900          369          1.3          2218            None
   serverside.counters        remove        {"_id": 1, "_types": 1}                            8         121         500          263          2.1          2111            True
   serverside.auth_sessions   update        {"session_key": 1}                                 7         111         684          277          1.0          1940            True
   serverside.credit_card     update        {"_id": 1}                                         5         145         764          368          0.0          1840            True
   serverside.email_alerts    remove        {"_types": 1, "request_code": 1}                   6         143         459          277          1.3          1663            False
   serverside.user            find          {"_id": 1, "_types": 1}                            5         153         427          320          1.9          1601            False
   serverside.user            update        {"emails.email": 1}                                2         218         422          320          0.7          640             True
   serverside.user            update        {"_id": 1}                                         2         139         278          208          0.4          417             True
   serverside.auth_sessions   update        {"session_endtime": 1, "session_userid": 1}        1         244         244          244          0.2          244             False
   serverside.game_level      find          {"_id": 1}                                         1         104         104          104          0.1          104             None


``--rounding``
^^^^^^^^^^^^^^

This option adjusts the rounding for calculated statistics like mean and
95%-ile.

For example:

.. code-block:: bash

   mloginfo mongod.log --queries --rounding 2

This option has no effect unless ``--queries`` is also specified.

Valid rounding values are from 0 to 4 decimal places. The default value is 1.


``--sort``
^^^^^^^^^^

This option can be used to sort the results of the ``--queries`` table, for
example:

.. code-block:: bash

   mloginfo mongod.log --queries --sort count
   mloginfo mongod.log --queries --sort sum

This option has no effect unless ``--queries`` is also specified.

Valid sort options are: ``namespace``, ``pattern``, ``count``, ``min``,
``max``, ``mean``, ``95%``, and ``sum``.

The default sort option is ``sum``.

Restarts (``--restarts``)
-------------------------

The restarts section will go through the log file and find all server restarts.
It will output a line per found restart, including the date and time and the
version.

For example:

.. code-block:: bash

   mloginfo mongod.log --restarts

In addition to the default information, this command will also output the
``RESTARTS`` section:

.. code-block:: bash

   RESTARTS

   Jul 17 09:11:37 version 2.2.2
   Jul 18 09:14:21 version 2.2.2
   Jul 18 15:53:51 version 2.4.6
   Jul 18 13:46:39 version 2.4.6
   Jul 19 18:30:04 version 2.4.6

Distinct (``--distinct``)
-------------------------

The distinct section goes through the log file and group all the lines together
by the type of message (it uses the "log2code" matcher). It will then output a
line per group, sorted by the largest group descending. This will return a good
overview of the log file of what kind of lines appear in the file.

This operation can take some time if the log file is big.

For example:

.. code-block:: bash

   mloginfo mongod.log --distinct

In addition to the default information, this command also outputs a list of
distinct messages grouped by message type, sorted by the number of matching
lines, as shown below.


.. code-block:: bash

   DISTINCT

   776367    connection accepted from ... # ... ( ... now open)
   776316    end connection ... ( ... now open)
    25526    info DFM::findAll(): extent ... was empty, skipping ahead. ns:
     9402    ERROR: key too large len: ... max:
       93    Btree::insert: key too large to index, skipping
        6    unindex failed (key too big?) ... key:
        5    old journal file will be removed:
        1    ClientCursor::yield can't unlock b/c of recursive lock ... ns: ... top:
        1    key seems to have moved in the index, refinding.

   distinct couldn't match 6 lines
   to show non-matched lines, run with --verbose.

If some lines can't be matched with the ``log2code`` matcher, the number of
unmatched lines is printed at the end. To show all the lines that couldn't be
matched, run mloginfo with the additional ``--verbose`` command.

Connections (``--connections``)
-------------------------------

The connections section returns general information about opened and closed
connections in the log file, as well as statistics of opened and closed
connections per unique IP address.

For example:

.. code-block:: bash

   mloginfo mongod.log --connections

In addition to the default information, this command also outputs connection
information as shown below.

.. code-block:: bash

   CONNECTIONS

        total opened: 156765
        total closed: 155183
       no unique IPs: 4
   socket exceptions: 915

   192.168.0.15      opened: 39758      closed: 39356
   192.168.0.17      opened: 39606      closed: 39207
   192.168.0.21      opened: 39176      closed: 38779
   192.168.0.24      opened: 38225      closed: 37841


Replica Set State Changes (``--rsstate``)
-----------------------------------------

Outputs information about every detected replica set state change.

For example:

.. code-block:: bash

   mloginfo mongod.log --rsstate

In addition to the default information, this command also outputs replica set
state changes.

.. code-block:: bash

   RSSTATE
   date               host                        state/message

   Oct 07 23:22:20    example.com:27017 (self)    replSet info electSelf 0
   Oct 07 23:22:21    example.com:27017 (self)    PRIMARY
   Oct 07 23:23:14    example.com:27017 (self)    replSet total number of votes is even - add arbiter or give one member an extra vote
   Oct 07 23:23:16    example.com:27018           STARTUP2
   Oct 07 23:23:32    example.com:27018           RECOVERING
   Oct 07 23:23:34    example.com:27018           SECONDARY

Transactions (``--transactions``)
---------------------------------

The transaction section will parse the log file to find information related
to transactions (MongoDB 4.0+). ``autocommit`` indicates whether ``autocommit``
was enabled for a transaction. The ``readConcern`` information is fetched
either from ``OperationContext`` or ``_txnResourceStash``. ``TimeActiveMicros``
and ``TimeInactiveMicros`` denote the number of micros active and inactive
during the span of the transaction. The ``duration`` field includes the value
in milliseconds and indicates the amount of time taken by each transaction.

For example:

.. code-block:: bash

   mloginfo mongod.log --transactions

In addition to the default information, this command will also output the
``TRANSACTIONS`` section:

.. code-block:: bash

 TRANSACTION

 DATETIME                       TXNNUMBER       AUTOCOMMIT      READCONCERN     TIMEACTIVEMICROS    TIMEINACTIVEMICROS   DURATION

 2019-06-18T12:31:03.180+0100           1         false         "snapshot"                 11142                     3   7
 2019-03-18T12:31:03.180+0100           2         false         "snapshot"                 11143                     4   6
 2019-07-18T12:31:03.180+0100           3         false         "snapshot"                 11144                     3   4
 2019-08-18T12:31:03.180+0100           4         false         "snapshot"                 11145                     4   7
 2019-06-18T12:31:03.180+0100           5         false         "snapshot"                 11146                     3   3

``--tsort``
^^^^^^^^^^^

This option can be used to sort the results of the ``--transaction`` table,
along with 'duration' keyword.

For example:

.. code-block:: bash

   mloginfo mongod.log --transaction --tsort duration

This option has no effect unless it is specified between ``--transaction`` and
``duration`` is specified.

Cursors (``--cursors``)
-----------------------------------------

Outputs information if a cursor was reaped for exceeding the transaction
timeout. The timestamp of transaction, Cursor ID, and the time at which the
cursor was reaped is captured from the logs.

For example:

.. code-block:: bash

   mloginfo mongod.log --cursors

.. code-block:: bash

   CURSOR

   DATETIME                            CURSORID    REAPEDTIME

   2019-06-14 12:31:04.180000+01:00    abc1        2019-06-18 12:31:04.180000+01:00
   2019-06-14 12:31:04.180000+01:00    abc2        2019-06-18 12:31:06.180000+01:00
   2019-06-14 12:31:04.180000+01:00    abc3        2019-06-18 12:31:08.180000+01:00

Storage Stats (``--storagestats``)
-----------------------------------------

Outputs information about the storage statistics for slow transactions.

For example:

.. code-block:: bash

   mloginfo mongod.log --storagestats

.. code-block:: bash

   STORAGE STATISTICS

   namespace                 operation    bytesRead    bytesWritten    timeReadingMicros    timeWritingMicros

   config.system.sessions    update       None         None            None                 None
   local.myCollection        insert       None         None            None                 None
   local.myCollection        update       None         None            None                 None
   local1.myCollection       insert       None         None            None                 None
   invoice-prod.invoices     insert       12768411     22233323        86313                12344
   invoice-prod.invoices     insert       12868411     22233323        86313                12344
