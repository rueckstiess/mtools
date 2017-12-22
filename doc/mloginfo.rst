.. _mloginfo:

========
mloginfo
========

**mloginfo** takes a log file and reports :ref:`default-info` about the
log file. The script also has some options for additional :ref:`info-sections`.


Usage
~~~~~

.. code-block:: bash

   mloginfo [-h] [--version] logfile
            [--verbose]
            [--queries] [--restarts] [--distinct] [--connections] [--rsstate]


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
total sum. The list is sorted by total sum (last column), which reflects the
overall work the database has to perform for each query pattern.

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

   namespace                    pattern                                        count    min (ms)    max (ms)    mean (ms)    sum (ms)

   serverside.scrum_master      {"datetime_used": {"$ne": 1}}                     20       15753       17083        16434      328692
   serverside.django_session    {"_id": 1}                                       562         101        1512          317      178168
   serverside.user              {"_types": 1, "emails.email": 1}                 804         101        1262          201      162311
   local.slaves                 {"_id": 1, "host": 1, "ns": 1}                   131         101        1048          310       40738
   serverside.email_alerts      {"_types": 1, "email": 1, "pp_user_id": 1}        13         153       11639         2465       32053
   serverside.sign_up           {"_id": 1}                                        77         103         843          269       20761
   serverside.user_credits      {"_id": 1}                                         6         204         900          369        2218
   serverside.counters          {"_id": 1, "_types": 1}                            8         121         500          263        2111
   serverside.auth_sessions     {"session_key": 1}                                 7         111         684          277        1940
   serverside.credit_card       {"_id": 1}                                         5         145         764          368        1840
   serverside.email_alerts      {"_types": 1, "request_code": 1}                   6         143         459          277        1663
   serverside.user              {"_id": 1, "_types": 1}                            5         153         427          320        1601
   serverside.user              {"emails.email": 1}                                2         218         422          320         640
   serverside.user              {"_id": 1}                                         2         139         278          208         417
   serverside.auth_sessions     {"session_endtime": 1, "session_userid": 1}        1         244         244          244         244
   serverside.game_level        {"_id": 1}                                         1         104         104          104         104

``--sort``
^^^^^^^^^^

This option can be used to sort the results of the ``--queries`` table, for
example:

.. code-block:: bash

   mloginfo mongod.log --queries --sort count
   mloginfo mongod.log --queries --sort sum

This option has no effect unless ``--queries`` is also specified.

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
