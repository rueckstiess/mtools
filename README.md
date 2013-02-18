# mtools

A collection of helper scripts to set up MongoDB test environments and
parse MongoDB log files (mongod, mongos). 


What's in the box?
------------------

The following tools are in the mtools collection:

* [mlogfilter](README.md#mlogfilter) -- slice log files by time, filter slow queries, find table scans, shorten log lines
* [mlogmerge](README.md#mlogmerge) -- merge several logfiles by time, includes time zone adjustments
* [mplotqueries](README.md#mplotqueries) -- visualize timed operations in the logfile, in/exclude namespaces, log scale optional
* [mlog2json](README.md#mlog2json) -- convert each line of a log file to a JSON document for mongoimport
* [mlaunch](README.md#mlaunch) -- a script to quickly spin up local mongod/mongos environments

Watch this spot, new tools will be added soon.

<hr>

Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only make
use the standard packages shipped with Python, and should run out of the box.

Some of the tools have additional dependencies, which are listed under the 
specific tool's section. See the [INSTALL.md](./INSTALL.md) file for installation 
instructions for these modules.

#### Python
You will need to have a version of Python installed for all the scripts
below, 2.7.x is recommended. 2.6.x will work but you need to install the `argparse` 
module separately (you can use `pip` to install it, see below). To check your
Python version, run `python --version` on the command line.

Python 3.x is currently not supported.


#### mtools installation

Clone the [mtools github repository](.) into a 
directory of your choice:

    cd /path/to/github/repos
    git clone git://github.com/rueckstiess/mtools.git

This will create a sub-folder `mtools` under the `/path/to/github/repos` folder 
and check out the code there. Make sure that the parent directory of mtools is set in 
your PYTHONPATH environment variable. If you use the _bash_ shell, you can do so by 
adding a line

    export PYTHONPATH=$PYTHONPATH:/parent/directory/of/mtools

to your `.bashrc` script. Other shells may have a different syntax.


#### Command style usage

While you can execute each of the scripts with `python script.py` ("script.py" being a
placeholder for the real script name), it is convenient to use the symbolic links
that are located in the `mtools/scripts/` subfolder.

Add the `mtools/scripts/` subfolder to your PATH environment variable, if you 
want to use the scripts from anywhere in the shell. If you use the _bash_ shell, 
you can do so by adding a line
    
    export PATH=$PATH:/path/to/github/repos/mtools/scripts

to your `.bashrc` script. Other shells may have a different syntax.


mlogfilter
----------

#### Description

A filter script to reduce the amount of information from MongoDB log files.  
Currently, the script supports filtering by time (from - to), to only show 
slow queries, to filter by arbitrary keywords, to detect table scans (heuristic)
or any combination of these filters. Additionally, the --shorten option can 
shorten log lines to the given value (default is 200 characters), cutting out
excess characters from the middle and replacing them with "...".


    usage: mlogfilter logfile [-h] [--from FROM] [--to TO] [--word WORDS] [--slow]
                         
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
      --slow                only output lines with query times longer than 1000 ms


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

mplotqueries
------------

#### Additional dependencies
- NumPy
- matplotlib

See the [INSTALL.md](./INSTALL.md) file for installation instructions of these dependencies.

#### Description

A script to plot query durations in a logfile (requires numpy and matplotlib packages).
    
    usage: mplotqueries filename [-h] [--ns [NS [NS ...]]] [--exclude-ns [NS [NS ...]]]
               
    positional arguments: 
      filename              log file to plot

    optional arguments:
      -h, --help                   show this help message and exit
      --ns [NS [NS ...]]           namespaces to include in the plot (default is all)
      --exclude-ns [NS [NS ...]]   namespaces to exclude from the plot
      --log                        plot y-axis in logarithmic scale (default=off)



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

