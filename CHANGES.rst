=================
Changes to mtools
=================

version 1.6.2
~~~~~~~~~~~~~
 * Update documentation to reference pip3 instead of pip (#774)
 * Document SSL parameters to mlaunch on website (#666)
 * Fix JSON serialize crash with bytes instead of str in pattern.py (#764)
 * mlaunch: `mlaunch list` throws typeError for a sharded deployment (#770)
 * mlaunch: Remove deprecated --sslWeakCertificateValidation
 * mloginfo: Add new --sharding section (#773)
 * mloginfo: Add --debug with some extra info on query patterns
 * mloginfo: Fix --verbose crash (#769)
 * mtransfer: Initial implementation of tool to export WiredTiger DBs (#754)

Thanks to @stennie, @michaelcahill, @Giuliano-C, @bugre, and @sindbach
for contributions to this release.

version 1.6.1
~~~~~~~~~~~~~
 * mtools should use python3 in shebangs (#761)
 * mloginfo: add timezone to mloginfo summary (#258)
 * mloginfo --clients: more robust parsing of client metadata (#765)
 * mloginfo --queries: fix missing patterns for remove command (#742)
 * mloginfo --queries: add rounding option (#698)
 * mplotqueries: fix error parsing checkpoint log line (#757)

Thanks to @stennie, @kallimachos, @kevinadi, @niccottrell, and @p-mongo
for contributions to this release.

version 1.6.0
~~~~~~~~~~~~~
Now supporting Python 3.6+ (only)

 * Add support for Python 3.7 and 3.8
 * Remove support for Python 2.7
 * Update requirements to modern package versions
 * Require minimum dependency versions rather than exact
 * mlaunch: mlaunch with no options should show --help (#749)
 * mlaunch: Fix --storageEngine confusingly reported as ignored in sharded
   deployments (#730)
 * mlaunch: Fix unquoted --wiredTigerEngineConfigString parameter (#683)
 * mloginfo: mloginfo with no options should show usage info (#751)
 * mloginfo: Fix for --queries gives AttributeError if there is a field called
   "query" in the log (#741)
 * mloginfo: Fix --queries gives `TypeError` for some logs (#697)
 * mloginfo: Add --checkpoints to show slow WiredTiger checkpoints if
   available (#707)
 * mloginfo: Improve --queries to show allowDiskUse for aggregations if
   available (#708)
 * mloginfo: Add --clients to show client summary info (#540)
 * mloginfo: Add --cursors to show cursor information if available (#710)
 * mloginfo: Add --storagestats to display storage statistics (#711)
 * mloginfo: Add --transactions to display slow transactions if available (#704)
 * mloginfo: Include queries without durations in the query count (#680)
 * mplotqueries: Fix --group-limit throws error in Python 3.x (#688)
 * mplotqueries: Add --dns to display slow DNS Resolutions if available (#706)
 * mplotqueries: Add --oplog to display slow oplog entries if available (#705)
 * Update mention of oldest non-EOL MongoDB server version (3.6 as of Jan 2020)
 * util/logfile.py: Reading log from stdin hits error on str.decode() in
   Python 3 (#658)

Thanks to @stennie, @kallimachos, @kevinadi, @savinay-vijay, @mitesh-gosavi,
@HenryGP, @sindbach, @garycahill, @karlvr, and @josemonteiro
for contributions to this release.

version 1.5.3
~~~~~~~~~~~~~
* mlaunch: Quote mongos --logpath (to handle paths with spaces)
* mlaunch: Permit command line options with "="
* mlaunch: Ignore passing unsupported param --wiredTigerCacheSizeGB to mongos
* mlaunch: Add --wiredTigerEngineConfigString as an undocumented mongod param
* util/logevent.py: Add LogEvent support for returning actual query (not pattern)

Thanks to @ajdavis, @renatoriccio, @twblamer, @kevinadi, @sindbach,
@kallimachos, and @stennie for contributions to this release.

version 1.5.2
~~~~~~~~~~~~~
* mlaunch: Set appname for MongoDB 3.4+ client metadata
* mlaunch: Only use roles variable instead of args once set up
* mlaunch: Fix for --sharded and --auth-role-docs failing to add roles
* mlaunch: Fix failure to connect to standalone SSL mongod
* mlaunch: Retain PyMongo import error exceptions
* mlogfilter: Fix Unicode error for redirected output
* Improve flake8 style compliance

Thanks to @kevinadi, @p-mongo, @gmishkin, and @stennie for contributions
to this release.

version 1.5.1
~~~~~~~~~~~~~
* mlaunch: Fix 1.5.0 regression preventing use of --auth
* mloginfo: Add support for MongoDB 3.2+ --rsinfo
* mlogfilter: Fix intermittent test failures

Thanks to @kevinadi, @kallimachos, @sindbach, and @stennie
for contributions to this release.

version 1.5.0
~~~~~~~~~~~~~
* Update matplotlib to 1.4.3
* Update numpy to 1.14.5
* Update python-dateutil to 2.7
* Update pymongo to 3.6.1
* Pin requirements to avoid pulling in breaking changes
* Ignore "new oplog query" log entries for query duration parsing
* Replace characters that can't be UTF decoded with '?'
* Fix logic error preventing parsing of empty or unexpected log lines
* mplotqueries: Report actual error when `matplotlib` import fails
* mlaunch: If `mongod` is missing, print the path that was used
* mlaunch: Add support for GSSAPI
* mlaunch: Add users to all shards in sharded cluster
* mlogvis: Remove write lock and read lock grouping

Thanks to @kevinadi, @jamesbroadhead, @mathom, @kallimachos,
@sindbach, and @stennie for contributions to this release!

version 1.4.1
~~~~~~~~~~~~~
* mlaunch: Fixes for Python 3.6.5 support (#596, #586)
* Include sys.version in --version output (#597)
* Migrate wiki pages to gh-pages and RST (#550, #550)
   - New documentation: http://blog.rueckstiess.com/mtools/

Thanks to @kallimachos, @sindbach, @kevinadi, @manfontan,
and @stennie for contributions to this release!

version 1.4.0
~~~~~~~~~~~~~

* Improve testing and documentation infrastructure (#542)
   - Add tox (#543)
   - Fix flake8 violations (#544)
   - Fix isort violations (#545)
   - Fix PEP 257 violations (#546)
   - Add RST documentation (#548)
* Make code compatible with both Python 2.7 and 3.6 (#527)
   - Add py36 environment for tox & Travis (#587)
* mlaunch: Error while creating replica set with name and auth args (#476)
* mlaunch: Testing for MongoDB 3.6 (#531)
* mlaunch: Using --hostname causes deploying failure in 3.6 (#554)
* mlaunch: psutil dependency missing (#557)
* mlaunch: Require shard servers to be replica sets (3.6.1+) (#567)
* mlaunch: Force `mlaunch --csrs` when "version" is `0.0.0` (#576)
* mlaunch: Create user with SCRAM-SHA-1 mechanism (#574)
* mlaunch: Allow starting 3.6 clusters with PyMongo 3.6.1 (#575)
* mlaunch: Use correct path separator according to OS (#584)
* mlaunch: Support path parameters containing spaces (#578)
* mlaunch: Update psutil requirement to 5.4.2 (#590)
* mloginfo: Test using current year rather than hardcoded value (#568)

Thanks to @kallimachos, @kevinadi, @sindbach, @ajdavis, @jaraco, @devkev,
@stephentunney, @shaneharvey, and @stennie for contributions to this release!

version 1.3.2
~~~~~~~~~~~~~

*  mloginfo: Add --connstats for connection duration metrics (#518)

Thanks to @nishantb10gen for contributions to this release!

version 1.3.1
~~~~~~~~~~~~~

*  mlaunch: support SSL parameters (#127)
*  mlaunch: make 8th+ replica set members non-voting (#528)
*  convert README to reStructuredText (#523)
*  update metadata in setup.py (#520)

Thanks to @ajdavis, @kallimachos, @kevinadi, and @josefahmad for contributions
to this release!

version 1.3.0
~~~~~~~~~~~~~

*  remove support for Python 2.6 (#469):
   https://github.com/rueckstiess/mtools/wiki/Notes:-Centos-6
*  deprecate support for End-of-Life versions of MongoDB (currently <3.0)
*  deprecate ``mgenerate`` in favor of ``mgeneratejs`` (#494)
*  add ``pip`` options to install/upgrade optional deps (PyMongo, numpy, ...)
   (#450, #464)
*  log tools should check if the file passed is a valid log file (#429)
*  allow analysis of log files with ctime format (#428)
*  add support for ``find`` commands in query section & log event processing
   (#465)
*  util/logevent.py: fixed incorrect timestamp processing (#490)
*  util/logevent.py: support WriteResult counters like nModified, nInserted
   (#386)
*  util/pattern.py line 15 wrong indentation level (#478)
*  mlaunch: support on Windows! (#488)
*  mlaunch: when a ``mongod`` fails to start, print log messages to stderr
   (#361)
*  mlaunch: fix tests for compat with MongoDB 3.0+ (#192)
*  mlaunch: --help should mention it accepts arbitrary ``mongod``/``mongos``
   flags (#356)
*  mlaunch: print error message for invalid options, rather than silently
   ignoring (#355)
*  mlaunch: --no-initial-user option for servers with auth (#487)
*  mlaunch: better error if --binarypath is wrong (#491)
*  mlaunch: changed default hostname to localhost (#510)
*  mlaunch: if unspecified, set wiredTigerCacheSizeGB to 1 (#517)
*  mlogfilter: error if invalid pattern provided (#483)
*  mlogfilter: calculate current year so rollover test will also work next
   year (#489)
*  mlogfilter: loops forever for some datetimes (#507)
*  mlogfilter: --component and --planSummary values should be case-insensitive
   (#505)
*  mloginfo: --queries should output progress to stderr (#255)
*  mplotqueries:  add chart --type docsExamined/n (#509)
*  mplotqueries:  default colors could be better (#453)
*  wiki: fix documentation mentioning "development mode" (#231)

Thanks to @kevinadi, @zhaoyi0113, @ajdavis, @geuscht-m, @TomerYakir, @devkev,
and @stennie for contributions to this release!

version 1.2.3
~~~~~~~~~~~~~

*  mlaunch: support for MongoDB 3.4 (#466)
*  mlaunch: MongoDB 3.3+ only supports CSRS for mongos --configdb parameter
   (#431)
*  mlaunch: CSRS feature breaks older configurations (#402)
*  mlaunch: improved parsing of the ``mongod`` version for RCs (#451)
*  mlaunch: New init --priority option forces first member primary
*  mlaunch: init & list now print username and password if auth enabled (#469)
*  mlaunch: --stop is now an alias of --kill to simplify auth shutdown (#363,
   #369, #333)

Thanks to @kevinadi, @Pash10g, @Steve-Hand, @vmenajr, and @ajdavis for
contributions to this release!

version 1.2.2
~~~~~~~~~~~~~

*  mgenerate: create operator for binary data  (#405)
*  mlaunch: added ``csrs`` parameter if version > 3.3
*  mlaunch: Allow one node config server with --csrs and make the default be
   one node (#438)
*  mlaunch: added ``shardsrv`` parameter automatically (#430)
*  mlaunch: fixed ``auth`` not working for replica sets (#380)
*  mlaunch: Make sure that when CSRS is deployed, --arbiter will not have an
   affect on it (#418)
*  mlaunch: Allow --setParameter options (#445)
*  mloginfo: fixed showing the host in ``rsstate`` (#410)
*  mloginfo: fixed check for WT engine (#426)

version 1.2.1
~~~~~~~~~~~~~

*  mlaunch: fix bug for CSRS feature that prevents older mlaunch configurations
   to start (#402)

version 1.2.0
~~~~~~~~~~~~~

*  mlaunch: support config servers as replica sets (CSRS) (#399, #401)
*  mlaunch: fix various ``mlaunch list`` errors (#396)
*  fix log file testing errors (#393)

version 1.1.9
~~~~~~~~~~~~~

*  mplotqueries: pin python-dateutil to version 2.2 because of problems with
   matplotlib (#377)
*  mplotqueries: fixed scaling issues with nscanned/n plots @devkev (#243,
   #379)
*  mlaunch: support for PyMongo 3.x @gormanb (#351)
*  better handling of invalid log lines due to line breaks @gianpaj (#375)
*  mloginfo: fixed bugs when reading from system.profile collection (#353)
*  mloginfo: includes geoNear commands in statistics (#344)
*  mgenerate: added more operators, like ``$concat``, ``$normal``, ``$zipf``
   (#360)
*  fixed false positives in the test suite

version 1.1.8
~~~~~~~~~~~~~

*  mloginfo: storage engine is now listed for log files (#330)
*  mplotqueries: x-axis bounds corrected when parsing multiple files (#322)
*  mlogfilter: truncated log lines ("too long ...") recognized and parsed as
   much as possible (#133)
*  better cross-platform script support, especially for windows users (#230)
*  logging components are updated to match final version of MongoDB 3.0 (#328,
   #327)
*  removed hard dependency on pymongo, only required if mlaunch is used (#337)
*  removed deprecated scripts like mlogversion, mlogdistinct (#336)
*  command in LogEvent is now always lowercase (#335)
*  LogEvent now has writeConflicts property (#334)
*  documented numpy minimum version 1.8.0 (#332)

version 1.1.7
~~~~~~~~~~~~~

*  mtools now understands 2.8 style log format, with severity and components.
    Added by @jimoleary (#269)
*  mlogfilter: added ``--command``, ``--planSummary``, ``--component`` and
   ``--level`` filters and allow multiple values for most filters (#239)
*  mloginfo: show host information and replica set name if available (#247)
*  mloginfo: added new section ``--rsinfo`` that prints replica set config
   information. Added by @jimoleary (#290)
*  mloginfo: now includes ``count`` and ``findAndModify`` commands in the
   statistics and adds operation column (#310)
*  mloginfo: version detection works for enterprise edition with SSL.
   Added by @gianpaj (#289)
*  mplotqueries: ability to adjust graphical properties of scatter plots,
   like opacity, marker size and edge. Added by @devkev (#309)
*  mlaunch: legacy mode for adding users with pymongo version < 2.5 (#221)
*  mlaunch: named shards now have correct name for single instances (#291)
*  mlaunch: ``list`` command was broken when other non-mtools instances were
   running. Added by @devkev (#297)
*  mlogvis: added options ``--no-browser`` and ``--out`` for mlogvis (#306)

version 1.1.6
~~~~~~~~~~~~~

*  mlogfilter: ``--thread`` now also matches "connection accepted" lines for
   that connection (#218, #219)
*  mlogfilter: fixed bug that would print milliseconds in timestamp twice in
   2.6 format for UTC timezone (#241)
*  mlaunch: allow overriding hostname for replica set setup (#256)
*  mlaunch: added a ``restart`` command (#253)
*  mlaunch: added ``--startup`` to ``list`` command to show all startup
   strings (#257)
*  mlaunch: aliased ``--verbose`` (now deprecated) as ``--tags`` (#257)
*  mloginfo: added ``--rsstate`` option to show all replica set state changes
   in log file. Added by @jimoleary (#228)
*  mloginfo: fixed issues with 95-percentile calculation. Added by @gianpaj
   (#238)
*  mloginfo: show host name and port if available (#247)
*  mloginfo: fixed bug where empty lines can't be parsed (#213)
*  mloginfo: show milliseconds for start/end (#245)
*  mloginfo: made numpy dependency optional for mloginfo. Added by @brondsem
   (#216)
*  mplotqueries: option to write output to image file instead of interactive
   mode. Added by @dpercy (#266)
*  mplotqueries: show correct timezone for time axis (#274)
*  mplotqueries: added option to allow fixing y-axis to specific min/max
   values (#214)

version 1.1.5
~~~~~~~~~~~~~

*  added workaround for compile errors with XCode 5.1 / clang 3.4 (#203)
*  mlaunch: fixed bug when using ``--binarypath`` and passing arguments
   through to mongod/mongos (#217)
*  mlaunch: fixed help text for default username and password (#207)
*  mlogfilter: "iso8601-local" timestamp format now working with ``--from``
   and ``--to`` (#209)
*  mplotqueries: fixed bug where "0ms" lines couldn't be plotted with durline
   plots (#208)
*  mgenerate: made it multi-threaded for performance boost (#204)
*  mgenerate: fixed bug when using custom port number (#217)
*  removed backward breaking ``total_seconds()`` from logevent parsing (#210)

version 1.1.4
~~~~~~~~~~~~~

*  performance improvements for log parsing (#187)
*  mloginfo ``--queries`` section to aggregate queries (#131)
*  mplotqueries: scatter plots now show "duration triangles" on double-click
   (#201)
*  mplotqueries: a number of bug fixes and stability improvements (#183, #199,
   #198, #191, #184)
*  mlaunch: a different ``--binarypath`` can be specified with
   ``mlaunch start`` (#181)
*  mlaunch: general bug fixes and tests (#178, #179, #176)
*  mlogfilter: timezone bug fixed (#186)
*  added sort pattern parsing to LogEvent and added query pattern parsing
   for system.profile events (#200)

For all changes, see the `closed issues tagged with milestone 1.1.4
<https://github.com/rueckstiess/mtools/issues?direction=desc&milestone=9&page=1&sort=updated&state=closed>`__

version 1.1.3
~~~~~~~~~~~~~

*  all tools can now read from system.profile collections as if it was a
   log file. Use this syntax as command line argument:
   "host:port/database.collection" (#164)
*  mtools now uses `Travis CI <https://travis-ci.org/rueckstiess/mtools>`__ for
   continuous integration testing
*  all log-parsing tools are now timezone aware. If no timezone is specified
   (all log files <= 2.4.x), then UTC is assumed (#174)
*  added new tool ``mgenerate`` to create structured randomized data for issue
   reproduction
*  mlaunch: Added a ``kill`` command to send SIGTERM or any other signal to
   all or a subset of instances (#168)
*  mlaunch: username + password is added for environments with
   ``--authentication``. Configurable username, password, database, roles.
   Thanks, ``@sl33nyc`` (#156)
*  mlaunch: start command can receive new arguments to pass through to
   mongos/d, and a different ``--binarypath`` (#151)
*  mlaunch: now checks in advance if port range is free, and warns if not
   (#166)
*  mlaunch: ``--version`` was removed by accident in 1.1.2. It's back now
   (#160)
*  mlogfilter: ``--thread``, ``--namespace`` and ``--operation`` filters
   can now be combined arbitrarily (#167)
*  mlogfilter: bug fix for when no log file was specified at command line.
   Now outputs clean error message (#124)
*  mplotqueries: added a compatibility check for matplotlib version 1.1.1
   for setting font size in legends (#128)

For all changes, see the `closed issues tagged with milestone 1.1.3 <https://github.com/rueckstiess/mtools/issues?direction=desc&milestone=8&page=1&sort=updated&state=closed>`__

version 1.1.2
~~~~~~~~~~~~~

*  mlaunch: completely rewritten, is now aware of the launched environment,
   commands: init, start, stop, list (#148)
*  mlaunch: mongos nodes start at beginning of port range for easier access
   (#145)
*  mlaunch: always uses absolute paths for the data directory, which shows
   up in ``ps aux | grep mongo`` output (#143)
*  mlogfilter: added filter masks ``--mask errors.log`` to search for
   correlations around certain events (#138)
*  mplotqueries: log parsing performance improvements for most plots
*  mlogvis: log parsing performance improvements
*  all tools: replaced shebang with ``#!/usr/bin/env python``, to support
   non-standard python installations

version 1.1.1
~~~~~~~~~~~~~

*  mplotqueries: introduced a new type of plot "durline", to visualize start
   and end of long-running operations
*  mplotqueries: use start times of operations that have a duration, rather
   than end time with ``--optime-start`` (#130)
*  mplotqueries: group by query pattern with ``--group pattern`` (#129)
*  mlaunch: allow more than 7 nodes, everyone above 7 is non-voting (#123)
*  mloginfo: fixed bug where anonymous Unix sockets can't be parsed (#121)

version 1.1.0
~~~~~~~~~~~~~

Simpler Structure
-----------------

Simplified tool structure. A lot of the mini-scripts have been combined.
There are only 5 scripts left: mlogfilter, mloginfo, mplotqueries, mlogvis,
mlaunch. No features have been cut, they are all still available within the
5 scripts, but may have moved.

New Features
------------

**mlogfilter**

* very fast binary search for time slicing
* timestamp-format aware, can convert between formats
* mlogmerge is now fully included into mlogfilter
* can output in json format

**mloginfo**

* mloginfo supports multiple files
* now with info sections on restarts, connections, distinct log lines
* shows progress bar during distinct log file parsing

**mplotqueries**

* can now group on arbitrary regular expressions
* has a new group limits feature, to group all but the top x groups together
* range plots support gaps
* better color scheme
* shows progress bar during log file parsing

**mlaunch**

* support multiple mongos

And Many Bug Fixes
------------------

For a full list of fixed issues, visit the `github issue page
<https://github.com/rueckstiess/mtools/issues>`__ of mtools.

version 1.0.5
~~~~~~~~~~~~~

*  mplotqueries: included a new plot type 'connchurn' that shows opened vs.
   closed connections over time (#77, #74).
*  mplotqueries: removed redundant ``--type duration`` plot and set the
   default to ``--type scatter --yaxis duration``.
*  mloginfo: new tool that summarizes log file information, including
   start/end time, version if present, and optionally restarts.
*  added nosetests infrastructure and first tests for mlaunch and mlogfilter
   (#39).
*  added internal LogFile class that offers helper methods around log files
   (#80).
*  fixed bug where ``mlogfilter --shorten`` was off by one character.

version 1.0.4
~~~~~~~~~~~~~

*  mlogvis: fixed a bug displaying the data in the wrong time zone (#70).
*  mplotqueries: fixed bug where a plot's argument sub-parser (e.g. for
   --bucketsize) couldn't deal with stdin.
*  mplotqueries: fixed bug that caused crash when there was no data to
   plot (#68).
*  mlogfilter: fixed bug that prevented ``--from`` and ``--to`` to be
   used with stdin (#73).
*  fixed bug parsing durations of log lines that have a float instead
   of int value (like 123.45ms).
*  implemented ISO-8601 timestamp format parsing for upcoming change
   in MongoDB 2.6 (#76).

version 1.0.3
~~~~~~~~~~~~~

*  mplotqueries: new plot types: "scatter" can plot various counters on the
   y-axis, "nscanned/n" plots inefficient queries (#58).
*  mplotqueries: added footnote ("created with mtools") including version.
   Can be toggled on/off with 'f' (#33).
*  mplotqueries: added histogram plots (--type histogram) with variable bucket
   size (#25).
*  mplotqueries: always plot full range of log file on x-axis, even if data
   points start later or end earlier (#60).
*  mlogfilter: added human-readable option (--human) that inserts ``,`` in
   large numbers and calculates durations in hrs,min,sec. (#8).
*  mlogdistinct: improved log2code matching and cleaned up log2code match
   database.

version 1.0.2
~~~~~~~~~~~~~

*  mlogvis: doesn't require web server anymore. Data is directly stored in
   self-contained HTML file (#57).
*  mlogvis: when clicking reset, keep group selection, only reset zoom
   window (#56).
*  mlaunch: different directory name will no longer create a nested
   ``data`` folder (#54).
*  mlaunch: arguments unknown to mlaunch are checked against mongod and
   mongos and only passed on if they are accepted (#55).
*  mlaunch: now you can specify a path for the mongod and mongos binaries
   with --binarypath PATH (#46).
*  mlaunch: positional argument for directory name removed. directory name
   now requires ``--dir``. default is ``./data``.

version 1.0.1
~~~~~~~~~~~~~

*  fixed timezone bug in mlogmerge (#24)
*  allow for multiple mongos in mlaunch with ``--mongos NUM`` parameter (#30)
*  mlaunch can now take any additional single arguments (like ``-vvv`` or
   ``--notablescan``) and pass it on to the mongod/s instances (#31)
*  all scripts now have ``--version`` flag (inherited from BaseCmdLineTool)
   (#34)
*  added ``--fast`` option to mlogfilter (#37)
*  mlogvis title added and legend height determined automatically (#45)
*  mlaunch now checks if port is available before trying to start and exits
   if port is already in use (#43)
*  improved mlogfilter ``--from`` / ``--to`` parsing, now supports sole
   relative arguments for both arguments, millisecond parsing, month-only
   filtering (#12).
*  restructured tools to derive from base class ``BaseCmdLineTool`` or
   ``LogFileTool``
*  fixed bug in log line parsing when detecting duration at the end of a line
*  changed ``--log`` to ``--logscale`` argument for mplotqueries to avoid
   confusion with "log" files
*  added `Contributing
   <https://github.com/rueckstiess/mtools/wiki/Development:-contributing-to-mtools>`__
   page under the tutorials section

version 1.0.0
~~~~~~~~~~~~~

This is the first version of mtools that has a version number. Some
significant changes to its unnumbered predecessor are:

*  installable via pip
*  directory re-organization: All tools are now located under
   ``mtools/mtools/``. This makes for easier ``PYTHONPATH`` integration, which
   will now have to point to the actual mtools directory, and not to the parent
   directory anymore. This is more in line with other Python projects.
*  ``mlogvis`` tool added: a simplified version of ``mplotqueries`` that
   doesn't require ``matplotlib`` dependency. Instead, it will run in a browser
   window, using `d3.js <https://www.d3js.org/>`__ for visualization.
   ``mlogvis`` is currently in BETA state.
*  introduced versioning: The version is stored in mtools/version.py and can be
   accessed programmatically from a Python shell with:

   .. code-block:: python

      import mtools
      mtools.__version__
