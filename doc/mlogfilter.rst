.. _mlogfilter:

==========
mlogfilter
==========

A script to reduce the amount of information from MongoDB log files.
**mlogfilter** takes one or several MongoDB log files as input, together with
some filter parameters, parses the contained log lines and outputs the lines
that match according to the filter parameters.

If several log files are provided, **mlogfilter** will merge them by timestamp
and insert a marker at the beginning of each line, before applying any of the
other filters.

Usage
~~~~~

.. code-block:: bash

   mlogfilter [-h] [--version] logfile [logfile ...]
              [--verbose] [--shorten [LENGTH]]
              [--human] [--exclude] [--json]
              [--timestamp-format {ctime-pre2.4, ctime, iso8601-utc, iso8601-local}]
              [--markers MARKERS [MARKERS ...]] [--timezone N [N ...]]
              [--namespace NS] [--operation OP] [--thread THREAD]
              [--slow [SLOW]]  [--fast [FAST]] [--scan]
              [--word WORD [WORD ...]]
              [--from FROM [FROM ...]] [--to TO [TO ...]]

**mlogfilter** can also be used with shell pipe syntax:

.. code-block:: bash

   cat logfile | mlogfilter [parameters]


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
   shows extra information about the parser and arguments. This is usually only
   needed for debugging purposes.

Shorten Log Lines
-----------------
``--shorten [LENGTH]``
   will shorten long lines to at most ``LENGTH`` characters, only showing the
   beginning and end of a line. If ``LENGTH`` is not provided, the default is
   200. This is useful to ensure that each log line fits into a shell / editor
   window to compare certain re-occurring values. The line is split in the
   middle and the excess characters are replaced with ``...``.

Human Readability
-----------------
``--human``
   makes log lines easier to read for humans. Long numbers will be separated by
   "thousands" comma separators, and the duration at the end of an operation is
   augmented with the hours, minutes and seconds for readability.

Exclude Log Lines
-----------------
``--exclude``
   This flag will invert the filter, excluding all the lines that match all
   filters, and only returning the non-matching lines.

JSON Output
-----------
``--json``
   If this flag is used, the output will be in JSON format instead of the
   regular log line string. Use this in conjunction with MongoDB's
   ``mongoimport`` to store the log file data in a MongoDB database.

   The values that are extracted and stored as separate fields in the resulting
   JSON document are (some may not > apply for all lines): ``line_str`` (the
   full line as string), ``split_tokens`` (the line as string tokens split on
   whitespace, stored as array of strings), ``datetime`` (the datetime for this
   line), ``operation``, ``thread``, ``namespace``, ``nscanned``,
   ``ntoreturn``, ``nreturned``, ``ninserted``, ``nupdated``, ``duration`` (the
   duration in milliseconds), ``r``, ``w`` (read or write lock times in
   microseconds), ``numYields`` (the number of yields for this operation)

   For example:

   .. code-block:: bash

      mlogfilter mongod.log --slow --json | mongoimport -d test -c mycoll

   This command would apply the "slow" filter to ``mongod.log`` and output the
   information as JSON, which can then be read my ``mongoimport``. The data is
   stored in the database ``test``, collection ``mycoll``. Each log line will
   be stored as a separate document.

Timestamp Format
----------------
``--timestamp-format FORMAT``
   Changes the timestamp format to the specified format. Possible formats are:

   -  ``ctime-pre2.4`` (the format looks like ``Fri Jul 26 11:38:37`` without
      milliseconds)
   -  ``ctime`` (the format looks like ``Fri Jul 26 11:38:37.712`` with
      milliseconds)
   -  ``iso8601-utc`` (the format looks like ``2013-07-26T11:38:37.712Z``)
   -  ``iso8601-local`` (the format looks like
      ``2013-07-26T11:38:37.712+0000``)

Merge Parameters
~~~~~~~~~~~~~~~~

The following parameters are useful if several log files are provided.
**mlogfilter** will merge the files based on the timestamp of each line, before
applying any other filters.

Merge Markers
-------------
``--markers M [M ...]``
   Markers help distinguish the source of merged log lines. Each merged line is
   preceded with a marker that indicates the original file. By default, the
   marker type is ``filename``. Another marker type can be specified, or custom
   markers can be provided. These are the available marker types:

   -  ``filename`` (the original filename in curly braces)
   -  ``enum`` (numeric markers ``{1}``, ``{2}``, ``{3}``, ...)
   -  ``alpha`` (letters ``{a}``, ``{b}``, ``{c}``, ...)
   -  ``none`` (no markers, this is useful if you merge log files form the
      same host but for different times)

Custom markers are also possible. Make sure the number of specified markers is
the same as the number of provided log files.

Timezone Adjustments
--------------------
``--timezone N [N ...]``
   The timezone parameter adjusts the timestamp of the log lines in hours. If
   one timezone value is provided, it is applied globally to all log lines. You
   can also adjust individual log files by providing the same number of
   timezone parameters as log files. Each log file is adjusted individually.
   For negative adjustments, the value has to be quoted, e.g. ``"-2"``.

For example:

.. code-block:: bash

   mlogfilter logfile1.log logfile2.log --timezone 4 0

This example would move the time of ``logfile1.log`` four hours into the
future, while keeping the time of ``logfile2.log`` constant.

.. _mlogfilter-filters:

Filter Parameters
~~~~~~~~~~~~~~~~~

The next set of parameters filter for certain log lines, and lines are only
returned if they match all the filters (if ``--exclude`` is set, a line is
returned if it would normally not be returned, i.e. if it does not match one or
more of the filters).

Namespace
---------
``--namespace NS``
   filter by namespace ``NS``, where ``NS`` has to be of the form
   ``<database>.<collection>``. Only lines matching this namespace are being
   returned. Note that the ``$`` sign can be matched by escaping it with
   ``\$``. Currently, only one namespace can be specified.

For example:

.. code-block:: bash

   mlogfilter mongod.log --namespace admin.\$cmd --slow 1000

This will return all admin commands that have been slower than 1 second.

Operation
---------
``--operation OP``
   filter by operation ``OP``, where ``OR`` can be any of ``query``,
   ``insert``, ``update``, ``delete``, ``command``, ``getmore``. Only the
   matching operations are returned. Currently, only one operation can be
   specified.

Thread
------
``--thread THREAD``
   filter by thread name (marked in square brackets after the timestamp in each
   line). This is useful to trace a single connection to the database.

For example:

.. code-block:: bash

   mlogfilter mongod.log --thread conn1234

This will return all lines that were issued from connection ``conn1234``. Note
that the initial line marking the opening of a connection (containing
``connection accepted``) itself is not on the same thread but on thread
``[initandlisten]``.

Pattern
-------
``--pattern P``
   filter by pattern ``P``, where ``P`` has to be a JSON string inside single
   quotes. A pattern is a transformation of a query into a canonicalized form,
   where values are replaced by ``1`` and fields are reordered alphabetically.
   Only query, update and remove operations matching this query pattern (also
   called "query shape") are being returned.

For example:

.. code-block:: bash

   mlogfilter mongod.log --pattern '{"_id": 1, "host": 1, "ns": 1}'

This will return all query, update and remove operations that match the pattern
``{"_id": 1, "host": 1, "ns": 1}``.

The field names must be surrounded by double quotes for valid JSON.

Duration
--------
``--slow MS``, ``--fast MS``
   returns only operations that are slower/faster than ``MS`` milliseconds. Not
   all lines in a log file have a duration, those without do not match the
   filter and are not being returned.

Collection Scans
----------------
``--scan``
   This flag attempts to detect queries that not using an index efficiently
   (scanning a large number of index keys relative to results) and returns only
   lines that match the detection heuristic. To match, a line has to have an
   ``nscanned`` value of 10000 or larger, and the ratio of ``n`` / ``nscanned``
   must be larger than 100. These values have proven useful to detect potential
   collection scans. For confirmed collection scans, instead use
   ``--planSummary COLLSCAN``.

Keywords
--------
``--word WORD [WORD ...]``
   Only lines that contain one or more of the provided words match this filter
   and are returned.

For example:

.. code-block:: bash

   mlogfilter mongod.log --word assert warning error

The below line matches all lines that contain any of the words ``assert``,
``warning``, ``error``:

Time Slicing
------------
``--from FROM [FROM ...]``, ``--to TO [TO ...]``
   These parameters slice the log file by time, by providing either a lower
   bound (``--from``) or an upper bound (``--to``) or both. This feature is
   implemented using binary search, making time slicing very fast and
   efficient. It should always be used if appropriate for the task. The
   arguments that can be passed into these parameters are quite flexible, and
   are explained below.

Both ``FROM`` and ``TO`` can accept the same format, which is defined as
``[DATE] [TIME] [OFFSET]`` separated by space. The square brackets indicate
that any of these parts can also be omitted.

``DATE`` can be any of:

-  a 3-letter weekday (e.g., ``Mon``, ``Wed``, ``Sun``, ...)
-  a date as 3-letter month and 1-2 digits day (e.g., ``Sep 5``, ``Jan 31``,
   ``Aug 08``, ...)
-  the words: ``today``, ``now``, ``start``, ``end``

``TIME`` can be any of

-  hours and minutes (e.g., ``20:15``, ``4:00``, ``3:25``, ...)
-  hours, minutes and seconds (e.g., ``13:30:01``, ``4:55:55``, ...)
-  hours, minutes, seconds and milliseconds (e.g., ``13:30:01.123``,
   ``4:55:55.700``, ...)

``OFFSET`` is again composed of ``OPERATOR````VALUE````UNIT`` (not separated by
spaces)

``OPERATOR`` is either ``+`` or ``-`` (the latter requires quotes as it would
otherwise be interpreted as another parameter by the argument parser.

``VALUE`` is any number.

``UNIT`` is one of the following:

-  ``s``, ``sec``
-  ``m``, ``min``
-  ``h``, ``hours``
-  ``d``, ``days``
-  ``w``, ``weeks``
-  ``mo``, ``months``
-  ``y``, ``years``

The ``OFFSET`` value is added / subtracted from the ``DATE````TIME`` value if
provided.

There are some rules for ease of use, that allow not to specify ``DATE`` and/or
``TIME``. The behavior should be intuitive, and examples are provided below.
Here are some of the rules:

**Weekdays**
if a weekday is provided without a date, the most recent day matching the
weekday is assumed.

For example, assuming the log file begins on ``Tue Aug 13 00:00:00`` and ends
on ``Fri Sep 9 15:31:10``

.. code-block:: bash

   mlogfilter mongod.log --from Wed 19:00

This example would return lines that are later than ``Wed Sep 6 19:00``.


**Months**
   if only a month is specified, the day is assumed to be ``1``.

For example, the following line matches everything from ``Sep 1 00:00:00``:

.. code-block:: bash

   mlogfilter mongod.log --from Sep

**Now**
   if the keyword ``now`` is specified for, it uses the current date and time.

For example, the following line matches everything from 5 minutes ago:

.. code-block:: bash

   mlogfilter mongod.log --from "now -5min"

**Today**
   if the keyword ``today`` is specified for ``DATE``, it uses the current date
   and the time ``00:00:00``

For example, the following line matches everything from *today* at ``00:00:00``
to *today* at ``02:00:00``:

.. code-block:: bash

   mlogfilter mongod.log --from today --to +2hours

**Start**
   if the keyword ``start`` is specified, it is replaced with the date and time
   of the beginning of the log file.

For example, the following line matches all but the first day (24h) of the log
file:

.. code-block:: bash

   mlogfilter mongod.log --from start +1day

**End**
   if the keyword ``end`` is specified, it is replaced with the date and time
   of the end of the log file

For example, the following line returns the last 20 minutes of a log file (note
the quotation marks):

.. code-block:: bash

   mlogfilter mongod.log --from "end -20min"

**Time**
   ``TIME`` can be combined with any of the keywords above and has precedence
   of the keyword time

For example, the following line matches everything from today at ``9:30``:

.. code-block:: bash

   mlogfilter mongod.log --from today 9:30

**Offset**
   if only an ``OFFSET`` is specified without ``DATE`` and/or ``TIME``, then it
   depends if the parameter was ``--from`` or ``--to``. For ``--from``, the
   offset is calculated from the start of the file, and for ``--to`` the offset
   is calculated from the ``--from`` time if provided, or otherwise from the
   end of the file.

For example, the following line matches the hour before the last hour in the
log file:

.. code-block:: bash

   mlogfilter mongod.log --from "end -2h" --to +1h
