Changes to mtools
=================

#### version 1.1.7

#### version 1.1.6

  * mlogfilter: `--thread` now also matches "connection accepted" lines for that connection (#218, #219)
  * mlogfilter: fixed bug that would print milliseconds in timestamp twice in 2.6 format for UTC timezone (#241)
  * mlaunch: allow overriding hostname for replica set setup (#256)
  * mlaunch: added a `restart` command (#253)
  * mlaunch: added `--startup` to `list` command to show all startup strings (#257) 
  * mlaunch: aliased `--verbose` (now depricated) as `--tags` (#257)
  * mloginfo: added `--rsstate` option to show all replica set state changes in log file. Added by @jimoleary (#228)
  * mloginfo: fixed issues with 95-percentile calculation. Added by @gianpaj (#238)
  * mloginfo: show host name and port if available (#247)
  * mloginfo: fixed bug where empty lines can't be parsed (#213)
  * mloginfo: show milliseconds for start/end (#245)
  * mloginfo: made numpy dependency optional for mloginfo. Added by @brondsem (#216)
  * mplotqueries: option to write output to image file instead of interactive mode. Added by @dpercy (#266)
  * mplotqueries: show correct timezone for time axis (#274)
  * mplotqueries: added option to allow fixing y-axis to specific min/max values (#214)


#### version 1.1.5

  * added workaround for compile errors with XCode 5.1 / clang 3.4 (#203)
  * mlaunch: fixed bug when using `--binarypath` and passing arguments through to mongod/mongos (#217)
  * mlaunch: fixed help text for default username and password (#207)
  * mlogfilter: "iso8601-local" timestmap format now working with `--from` and `--to` (#209)
  * mplotqueries: fixed bug where "0ms" lines couldn't be plotted with durline plots (#208)
  * mgenerate: made it multi-threaded for performance boost (#204)
  * mgenerate: fixed bug when using custom port number (#217)
  * removed backward breaking `total_seconds()` from logevent parsing (#210)


#### version 1.1.4

  * performance improvements for log parsing (#187)
  * mloginfo `--queries` section to aggregate queries (#131)
  * mplotqueries: scatter plots now show "duration triangles" on double-click (#201)
  * mplotqueries: a number of bug fixes and stability improvements (#183, #199, #198, #191, #184)
  * mlaunch: a different `--binarypath` can be specified with `mlaunch start` (#181)
  * mlaunch: general bug fixes and tests (#178, #179, #176)
  * mlogfilter: timezone bug fixed (#186)
  * added sort pattern parsing to LogEvent and added query pattern parsing for system.profile events (#200)

For all changes, see the [closed issues tagged with milestone 1.1.4](https://github.com/rueckstiess/mtools/issues?direction=desc&milestone=9&page=1&sort=updated&state=closed)

#### version 1.1.3

  * all tools can now read from system.profile collections as if it was a logfile. Use this syntax as command line argument: "host:port/database.collection" (#164)
  * mtools now uses [Travis CI](https://travis-ci.org/rueckstiess/mtools) for continuous integration testing
  * all log-parsing tools are now timezone aware. If no timezone is specified (all log files <= 2.4.x), then UTC is assumed (#174)
  * added new tool `mgenerate` to create structured randomized data for issue reproduction
  * mlaunch: Added a `kill` command to send SIGTERM or any other signal to all or a subset of instances (#168)
  * mlaunch: username + password is added for environments with `--authentication`. Configurable username, password, database, roles. Thanks, @sl33nyc (#156) 
  * mlaunch: start command can receive new arguments to pass through to mongos/d, and a different `--binarypath` (#151)
  * mlaunch: now checks in advance if port range is free, and warns if not (#166)
  * mlaunch: `--version` was removed by accident in 1.1.2. It's back now (#160)
  * mlogfilter: `--thread`, `--namespace` and `--operation` filters can now be combined arbitrarily (#167)
  * mlogfilter: bugfix for when no log file was specified at command line. Now outputs clean error message (#124)
  * mplotqueries: added a compatibility check for matplotlib version 1.1.1 for setting fontsize in legends (#128)

For all changes, see the [closed issues tagged with milestone 1.1.3](https://github.com/rueckstiess/mtools/issues?direction=desc&milestone=8&page=1&sort=updated&state=closed)

#### version 1.1.2

  * mlaunch: completely rewritten, is now aware of the launched environment, commands: init, start, stop, list (#148)
  * mlaunch: mongos nodes start at beginning of port range for easier access (#145)
  * mlaunch: always uses absolute paths for the data directory, which shows up in `ps aux | grep mongo` output (#143)
  * mlogfilter: added filter masks `--mask errors.log` to search for correlations around certain events (#138)
  * mplotqueries: log parsing performance improvements for most plots
  * mlogvis: log parsing performance improvements
  * all tools: replaced shebang with `#!/usr/bin/env python`, to support non-standard python installations
  

#### version 1.1.1

  * mplotqueries: introduced a new type of plot "durline", to visualize start and end of long-running operations
  * mplotqueries: use start times of operations that have a duration, rather than end time with `--optime-start` (#130)
  * mplotqueries: group by query pattern with `--group pattern` (#129)
  * mlaunch: allow more than 7 nodes, everyone above 7 is non-voting (#123)
  * mloginfo: fixed bug where anonymous unix sockets can't be parsed (#121)


#### version 1.1.0

###### Simpler Structure

Simplified tool structure. A lot of the mini-scripts have been combined. There are only 5 scripts left: mlogfilter, mloginfo, mplotqueries, mlogvis, mlaunch. No features have been cut, they are all still available within the 5 scripts, but may have moved. 

###### New Features

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


###### And Many Bug Fixes

For a full list of fixed issues, visit the [github issue page](https://github.com/rueckstiess/mtools/issues) of mtools.


#### version 1.0.5

  * mplotqueries: included a new plot type 'connchurn' that shows opened vs. closed connections over time (#77, #74).
  * mplotqueries: removed redundant `--type duration` plot and set the default to `--type scatter --yaxis duration`.
  * mloginfo: new tool that summarizes log file information, including start/end time, version if present, and optionally restarts.
  * added nosetests infrastructure and first tests for mlaunch and mlogfilter (#39).  
  * added internal LogFile class that offers helper methods around log files (#80).
  * fixed bug where `mlogfilter --shorten` was off by one character.

#### version 1.0.4

  * mlogvis: fixed a bug displaying the data in the wrong time zone (#70).
  * mplotqueries: fixed bug where a plot's argument sub-parser (e.g. for --bucketsize) couldn't deal with stdin.
  * mplotqueries: fixed bug that caused crash when there was no data to plot (#68).
  * mlogfilter: fixed bug that prevented `--from` and `--to` to be used with stdin (#73).
  * fixed bug parsing durations of log lines that have a float instead of int value (like 123.45ms).
  * implemented ISO-8601 timestamp format parsing for upcoming change in MongoDB 2.6 (#76).

#### version 1.0.3

  * mplotqueries: new plot types: "scatter" can plot various counters on the y-axis, "nscanned/n" plots inefficient queries (#58).
  * mplotqueries: added footnote ("created with mtools") including version. Can be toggled on/off with 'f' (#33).
  * mplotqueries: added histogram plots (--type histogram) with variable bucket size (#25).
  * mplotqueries: always plot full range of logfile on x-axis, even if data points start later or end earlier (#60).
  * mlogfilter: added human-readable option (--human) that inserts `,` in large numbers and calculates durations in hrs,min,sec. (#8).
  * mlogdistinct: improved log2code matching and cleaned up log2code match database.

#### version 1.0.2

  * mlogvis: doesn't require webserver anymore. Data is directly stored in self-contained html file (#57).
  * mlogvis: when clicking reset, keep group selection, only reset zoom window (#56).
  * mlaunch: different directory name will no longer create a nested `data` folder (#54).
  * mlaunch: arguments unknown to mlaunch are checked against mongod and mongos and only passed on if they are accepted (#55).
  * mlaunch: now you can specify a path for the mongod and mongos binaries with --binarypath PATH (#46).
  * mlaunch: positional argument for directory name removed. directory name now requires `--dir`. default is `./data`.

#### version 1.0.1

  * fixed timezone bug in mlogmerge (#24)
  * allow for multiple mongos in mlaunch with `--mongos NUM` parameter (#30)
  * mlaunch can now take any additional single arguments (like `-vvv` or `--notablescan`) and pass it on to the mongod/s instances (#31)
  * all scripts now have `--version` flag (inherited from BaseCmdLineTool) (#34)
  * added `--fast` option to mlogfilter (#37)
  * mlogvis title added and legend height determined automatically (#45)
  * mlaunch now checks if port is available before trying to start and exits if port is already in use (#43)
  * improved mlogfilter `--from` / `--to` parsing, now supports sole relative arguments for both arguments, millisecond parsing, month-only filtering (#12).
  * restructured tools to derive from base class `BaseCmdLineTool` or `LogFileTool`
  * fixed bug in logline parsing when detecting duration at the end of a line
  * changed `--log` to `--logscale` argument for mplotqueries to avoid confusion with "log" files
  * added [Contributing](tutorials/contributing.md) page under the tutorials section

#### version 1.0.0

This is the first version of mtools that has a version number. Some significant changes to its unnumbered predecessor are:

  * installable via pip
  * directory re-organization: All tools are now located under `mtools/mtools/`. This makes for easier `PYTHONPATH` integration, which will now have to point to the actual mtools directory, and not to the parent directory anymore. This is more in line with other Python projects.
  * `mlogvis` tool added: a simplified version of `mplotqueries` that doesn't require `matplotlib` dependency. Instead, it will run in a browser window, using [d3.js](http://www.d3js.org/) for visualization. `mlogvis` is currently in BETA state.
  * introduced versioning: The version is stored in mtools/version.py and can be accessed programmatically from a Python shell with

        import mtools
        mtools.__version__
