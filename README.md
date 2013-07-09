# mtools

[![PyPI version](https://badge.fury.io/py/mtools.png)](http://badge.fury.io/py/mtools)

A collection of helper scripts to set up MongoDB test environments and
parse MongoDB log files (mongod, mongos). 


What's in the box?
------------------

The following tools are in the mtools collection:

* [mlogfilter](#mlogfilter) -- slice log files by time, filter slow queries, find table scans, shorten log lines
* [mlogversion](#mlogversion) -- auto-detect the version number of a mongos/mongod log file
* [mlogdistinct](#mlogdistinct) -- groups all similar log messages together and displays their counts
* [mlogmerge](#mlogmerge) -- merge several logfiles by time, includes time zone adjustments
* [mlog2json](#mlog2json) -- convert each line of a log file to a JSON document for mongoimport
* [mplotqueries](#mplotqueries) -- visualize logfiles with different types of plots (requires matplotlib)
* [mlogvis](#mlogvis) -- creates a self-contained html file that shows a visualization in a web browser
* [mlaunch](#mlaunch) -- a script to quickly spin up local mongod/mongos environments (requires pymongo)


Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only make
use the standard packages shipped with Python, and should run out of the box.

Some of the tools have additional dependencies, which are listed under the 
specific tool's section. See the [INSTALL.md](./INSTALL.md) file for installation 
instructions for these modules.


Recent Changes
--------------
The current version of mtools is 1.0.1. See [CHANGES.md](./CHANGES.md) for a list of changes from previous versions of mtools.


Contribute to mtools
--------------------
If you'd like to contribute to mtools, please read the [contributor page](tutorials/contributing.md) for instructions.


<hr>

mlogfilter
----------

#### Description

A filter script to reduce the amount of information from MongoDB log files.  
Currently, the script supports filtering by time (from - to), to only show 
slow/fast queries, to filter by arbitrary keywords, to detect table scans (heuristic)
or any combination of these filters. Additionally, the --shorten option can 
shorten log lines to the given value (default is 200 characters), cutting out
excess characters from the middle and replacing them with "...".


    usage: mlogfilter logfile [options]

    positional arguments:
      logfile               logfile to parse

    optional arguments:
      -h, --help            show this help message and exit
      --from FROM           output starting at FROM
      --to TO               output up to TO
      --shorten [LENGTH]    shortens long lines by cutting characters out of the
                            middle until the length is <= LENGTH (default 200)
      --scan                only output lines which appear to be table scans (if
                            nscanned>10000 and ratio of nscanned to nreturned>100)
      --word WORDS          only output lines matching any of WORDS
      --slow [SLOW]         only output lines with query times longer than SLOW ms
                            (default is 1000)
      --fast FAST           only output lines with query times shorter than FAST ms


    FROM and TO can be any combination of [DATE] [TIME] [OFFSET] in that order,
    separated by space.

        [DATE] can be any of
            - a 3-letter weekday (Mon, Tue, Wed, ...)
            - a date as 3-letter month, 1-2 digits day (Sep 5, Jan 31, Aug 08)
            - the words: today, now, start, end

        [TIME] can be any of
            - hours and minutes (20:15, 04:00, 3:00)
            - hours, minutes and seconds (13:30:01, 4:55:55)

        [OFFSET] consists of [OPERATOR][VALUE][UNIT]   (no spaces in between)

        [OPERATOR] can be + or - (note that - can only be used if the whole 
            "[DATE] [TIME] [OFFSET]" is in quotation marks, otherwise it would 
            be confused with a separate parameter)

        [VALUE] can be any number

        [UNIT] can be any of s, sec, m, min, h, hours, d, days, w, weeks, mo,
            months, y, years

        The [OFFSET] is added/subtracted to/from the specified [DATE] [TIME].

        For the --from parameter, the default is the same as 'start' 
            (0001-01-01 00:00:00). If _only_ an [OFFSET] is given, it is 
            added to 'start' (which is not very useful).

        For the --to parameter, the default is the same as 'end' 
            (9999-31-12 23:59:59). If _only_ an [OFFSET] is given, however, 
            it is added to [FROM].


        Examples:  
            --from Sun 10:00 
                goes from last Sunday 10:00:00am to the end of the file

            --from Sep 29
                goes from Sep 29 00:00:00 to the end of the file

            --to today 15:00
                goes from the beginning of the file to today at 15:00:00

            --from today --to +1h
                goes from today's date 00:00:00 to today's date 01:00:00

            --from 20:15 --to +3m  
                goes from today's date at 20:15:00 to today's date at 20:18:00



<hr> 


mlogversion
-----------

#### Description

Takes a logfile and tries to detect the version of the mongos/mongod process that wrote this file. It does so by matching each line of the logfile to its originating line in the source code. For each line, it keeps track of the version that the matching code line came from. 

Whenever the tool encounters a line that limits the set of possible versions further, it will output this particular line and state the remaining possible versions.

If a server restart is detected, and thus the real version of the logfile is revealed, it will state this also.

This tool builds on top of the code2line module within mtools and is currently in BETA state. If you find any problems using this tool, please report it through the github issue tracker on this page.

    usage: mlogversion logfile [-h | --help]
    

<hr>

mlogdistinct
------------

#### Description

Groups all similar log messages in the logfile together and only displays a distinct set of messages (one for each group) and the number of matches in the logfile. "Similar" here means that all log messages originate from the same code line in the source code, but may have different variable parts.

This tool builds on top of the code2line module within mtools and is currently in BETA state. If you find any problems using this tool, please report it through the github issue tracker on this page. It would also be helpful to get any log lines that you think should have been matched. Use `--verbose` to output the lines that couldn't be matched.

    usage: mlogdistinct logfile [-h | --help] [--verbose]

Example output:

    776367    connection accepted from ... # ... ( ... now open)
    776316    end connection ... ( ... now open)
     25526    info DFM::findAll(): extent ... was empty, skipping ahead. ns:
      9402    ERROR: key too large len: ... max:
        93    Btree::insert: key too large to index, skipping
         6    unindex failed (key too big?) ... key:
         5    old journal file will be removed:
         1    ClientCursor::yield can't unlock b/c of recursive lock ... ns: ... top:
         1    key seems to have moved in the index, refinding.


<hr>

mlogmerge
---------

#### Description

A script that takes log files as input and merges them by date/time. Each line receives an additional "tag", which
indicates the original file name. Tags can be generated automatically, different styles (enum, alpha, filename) are
available, or you can provide custom tags, for example "[PRI] [SEC] [ARB]".
    
    usage: mlogmerge logfiles [-h | --help] [--label LABELS] [--pos POS]

    positional arguments: 
      logfiles              list of logfiles to merge

    optional arguments:
      -h, --help            show this help message and exit
      --labels LABELS       either one of 'enum' (default), 'alpha', 
                            'filename', 'none' or a list of labels (must
                            match number of logfiles)
      --pos POS             position where label is printed in line. 
                            either a number (default: 4) or 'eol'
      --timezone [N [N ..]] timezone adjustments: add N hours to 
                            corresponding log file. If only one number
                            is given, adjust globally


<hr>


mlog2json
---------

#### Description

A script to convert mongod/mongos log files to JSON. The script extracts information
from each line of the log file and outputs a JSON document for each line.  
    
    usage: mlog2json logfile [-h]
               
    positional arguments: 
      logfile              log file to convert

    optional arguments:
      -h, --help           show this help message and exit


A common usecase for this tool is to import the JSON documents back into mongodb for
further processing. This can easily be done with `mongoimport`. The usage is:

    mlog2json logfile | mongoimport -d DATABASE -c COLLECTION

You need a running mongod/mongos process to import the data.

<hr> 

mplotqueries
------------

#### See also 

A [tutorial for mplotqueries](./tutorials/mplotqueries.md) is available in the tutorials subfolder. It will walk you through all the features that mplotqueries currently contains.

#### Additional dependencies
- NumPy
- matplotlib

See the [INSTALL.md](./INSTALL.md) file for installation instructions of these dependencies.

#### Description

<img src="https://www.dropbox.com/s/obff0srk45rzmum/mplotqueries_screenshot.png?dl=1" border=0>

A script to plot query durations from a logfile (requires numpy and matplotlib packages).

###### Groups
The operations can be grouped (colored) differently, by namespace (default, or with `--group namespace`), 
type of operation, like query, insert, update, remove, getmore, command (with `--group operation`) or by 
thread/connection (with `--group thread`).

The first 9 groups can be individually toggled to hide/show with the keys 1-9. Pressing 0 hides/shows
all groups.

###### Clickable
Clicking on any of the plot points or lines will print the corresponding log line to stdout. Make sure that
you're not in zoom mode anymore or the click won't get registered.

###### Overlays
Overlays allow you to create several different plots (each with a call to mplotqueries) and
overlay them all to create a single plot. One way to achieve this is to specify several filenames
instead of just one. The files are combined and visualized in a single plot.

Sometimes, this isn't possible or practical, for example if the output you want to plot comes from
a preprocessing pipe, for example created with grep or mlogfilter. Or you want to use different
parameters (`--group` or `--type`) for different plots. In these cases, you can create overlays with
the `--overlay` option. A plot will be temporarily stored on disk (under `~/.mtools/mplotqueries/overlays)`, 
instead of plotted. You can add as many overlays as you like. The first call without the `--overlay`
option will additionally plot all existing overlays. To remove overlays, run mplotqueries with `--reset`.

###### Different types of plots
By default, mplotqueries uses a "duration" plot, that plots the duration of each logline as a point in a 
2D coordinate system, where the x-axis is the time of the event, and the y-axis is the duration it took. 
With the parameter `--type`, a different plot type can be chosen. Currently, there are 3 basic types:
"duration", "event" and "range". The "event" plot will plot each log line as a vertical line on the
x-axis. Use `mlogfilter` or `grep` to extract the events from the log file that are of interest. Range plots
will plot a horizontal bar from the datetime of the first line to the datetime of the last line. This plot 
type is useful to show time periods or ranges. As an example, you could compare the coverage and overlap of 
several log files.

Apart from these three basic plot types, it is easy to create new plot types that derive from any of the 
basic ones. Currently, there is one derived plot type, called `rsstate`. This plot type is a special type 
of event plot, that specifically looks at the replica set state changes (PRIMARY, SECONDARY, ...) and 
plots them as vertical lines.
  
###### Usage  
    mplotqueries filename [filename ...] [-h] [--ns [NS [NS ...]]] [--exclude-ns [NS [NS ...]]]
               
    positional arguments: 
      filename              log file(s) to plot

    optional arguments:
      -h, --help                   show this help message and exit
      --ns [NS [NS ...]]           namespaces to include in the plot (default is all)
      --exclude-ns [NS [NS ...]]   namespaces to exclude from the plot
      --log                        plot y-axis in logarithmic scale (default=off)
      --no-legend                  turn off legend (default=on)
      --reset                      removes all stored overlays. See --overlay for more
                                   information.
      --overlay                    plots with this option will be stored as 'overlays'
                                   but not plotted. They are all drawn with the first
                                   call without --overlay. Use --reset to remove all
                                   overlays.
      --type TYPE                  choose the type of plot. Currently, the types are
                                   duration, event, range, rsstate.
      --group GROUP                each plot type has different supported groups. Most
                                   plot types support grouping by namespace (default), 
                                   operation or thread.

<hr>

mlogvis
-------

#### Description

A script to visualize logfiles in a browser, using the d3.js javascript visualization engine.
`mlogvis` is a prototype that implements a sub-set of features of mplotqueries without the 
matplotlib dependency. Eventually, the two scripts will merge into one. 

The script will read a logfile, process the data and write a self-contained html file 
to the current working directory. It will then start open a browser tab to display the file.
The html file can also be sent to somebody and openend by any modern browser. Internet
connection required for dynamic loading of d3 javascript library.

###### Usage  

usage: mlogvis [-h] logfile

    mongod/mongos log file visualizer (browser edition). Extracts information from
    each line of the log file and outputs a html file that can be viewed in a browser.
    Automatically opens a browser tab and shows the file.

    positional arguments:
      logfile     logfile to visualize.

    optional arguments:
      -h, --help  show this help message and exit

<hr>

mlaunch
-------

##### Additional dependencies
- pymongo 

See the [INSTALL.md](./INSTALL.md) file for installation instructions of these dependencies.

#### Description

This script lets you quickly spin up MongoDB environments on your local
machine. It supports various configurations of stand-alone servers, 
replica sets and sharded clusters.

    usage: mlaunch [-h] (--single | --replicaset) [--nodes NUM] [--arbiter]
                   [--name NAME] [--sharded [N [N ...]]] [--config NUM]
                   [--verbose] [--port PORT] [--authentication]
                   [--loglevel LOGLEVEL]
                   [dir]

    script to launch MongoDB stand-alone servers, replica sets, and shards

    positional arguments:
      dir                   base directory to create db and log paths

    optional arguments:
      -h, --help            show this help message and exit
      --single              creates a single stand-alone mongod instance
      --replicaset          creates replica set with several mongod instances
      --nodes NUM           adds NUM data nodes to replica set (requires
                            --replicaset, default: 3)
      --arbiter             adds arbiter to replica set (requires --replicaset)
      --name NAME           name for replica set (default: replset)
      --sharded [N [N ...]]
                            creates a sharded setup consisting of several singles
                            or replica sets. Provide either list of shard names or
                            number of shards (default: 1)
      --config NUM          adds NUM config servers to sharded setup (requires
                            --sharded, NUM must be 1 or 3, default: 1)
      --verbose             outputs information about the launch
      --port PORT           port for mongod, start of port range in case of
                            replica set or shards (default: 27017)
      --authentication      enable authentication and create a key file and admin
                            user (admin/mypassword)
      --loglevel LOGLEVEL   increase loglevel to LOGLEVEL (default: 0)


#### Examples

Launch single mongod instance

    mlaunch --single

Launch replica set with 2 data nodes and 1 arbiter, use authentication

    mlaunch --replicaset --nodes 2 --arbiter --authentication

Launch sharded cluster with 2 shards, each consisting of a replicaset with 3 nodes, increase loglevel to 3

    mlaunch --sharded 2 --replicaset --loglevel 3

Launch sharded cluster with 3 shards called tic, tac and toe, each of them a single mongod, add 3 config servers 
start from port 30000, and print mongod commands used

    mlaunch --sharded tic tac toe --single --config 3 --port 30000 --verbose

<hr>

mtools combined
---------------

The scripts in the mtools collection can be used with the shell pipe syntax and can be easily 
combined to quickly create complex analytical queries.

Example:

    mlogmerge mongod_prim.log mongod_sec.log mongod_arb.log --label [pri] [sec] [arb] | 
        grep -v writebacklisten | 
        mlogfilter --slow --from Jan 30 20:16 --to +1h | 
        mplotqueries --log

This combination of commands merges the log files of a primary, secondary, and arbiter node, 
removes the 300 second writebacklisten commands, filters out only the slow queries from Jan 30 
at 20:16pm for 1 hour, and then plots the results.    

