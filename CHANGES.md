Changes to mtools
=================

#### version 1.1.2

  * mlogfilter: added filter masks `--mask errors.log` to search for correlations around certain events (#138)
  * mlaunch: mongos nodes start at beginning of port range for easier access (#145)
  * mlaunch: always uses absolute paths for the data directory, which shows up in `ps aux | grep mongo` output (#143)
  * mplotqueries: log parsing performance improvements for most plots
  

#### version 1.1.1

  * mplotqueries: introduced a new type of plot "durline", to visualize start and end of long-running operations.
  * mplotqueries: use start times of operations that have a duration, rather than end time with `--optime-start` (#130)
  * mplotqueries: group by query pattern with `--group pattern` (#129).
  * mlaunch: allow more than 7 nodes, everyone above 7 is non-voting (#123).
  * mloginfo: fixed bug where anonymous unix sockets can't be parsed (#121).


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
