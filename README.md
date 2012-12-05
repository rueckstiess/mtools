# mtools

A collection of helper scripts to set up MongoDB test environments and
parse MongoDB log files (mongod, mongos). 


Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only make
use the standard packages shipped with Python, and should run out of the box.

Some of the tools have additional dependencies, which are listed under the 
specific tool's section. See the [INSTALL.md](https://github.com/rueckstiess/mtools/blob/master/INSTALL.md) file for installation 
instructions for these modules.

#### Python
You will need to have a version of Python installed for all the scripts
below, 2.7.x is recommended. 2.6.x will work but you need to install the `argparse` 
module separately (you can use `pip` to install it, see below). To check your
Python version, run `python --version` on the command line.

Python 3.x is currently not supported.


#### mtools installation

Clone the [mtools github repository](https://github.com/rueckstiess/mtools) into a 
directory of your choice:

	cd /path/to/github/repos
    git clone git://github.com/rueckstiess/mtools.git

This will create a sub-folder `mtools` under the `/path/to/github/repos` folder 
and check out the code there.


#### Command style usage

If you want to execute the scripts in "command style", i.e. typing 
`script --parameter` instead of `python script.py --parameter`, you need to create 
simlinks in a directory that is in your PATH environment variable:

Let's assume `/path/in/env` is a path that is part of your PATH environment 
(check with `echo $PATH` from your command line prompt). To add a simlink to the
`mlaunch.py` script, run:

    cd /path/in/env
    ln -s /path/to/github/repos/mtools/mlaunch.py mlaunch

Also check that the _executable_ flag is set on mlaunch.py, with

    cd /path/to/github/repos/mtools
    ls -la

The tools you want to execute directly should have the `x` flag set for at least "user", 
e.g. `-rwxr--r--`. If this isn't the case, you can set it with

    chmod u+x mlaunch.py

You should now be able to use the mlaunch.py script from any directory by just 
typing `mlaunch` (and any additional parameters).


<hr>

mlaunch
-------

##### Additional dependencies
- pymongo 

See the [INSTALL.md](https://github.com/rueckstiess/mtools/blob/master/INSTALL.md) file for installation instructions of these dependencies.

#### Description

This script lets you quickly spin up MongoDB environments on your local
machine. It supports various configurations of stand-alone servers, 
replica sets and sharded clusters.

    usage: mlaunch [-h] (--single | --replicaset) [--nodes NUM] [--arbiter]
                   [--name NAME] [--sharded [NAME [NAME ...]]] [--config NUM]
                   [--port PORT] [--verbose]
                   [dir]

    script to launch MongoDB stand-alone servers, replica sets, and shards

    positional arguments:
      dir                   base directory to create db and log paths

    optional arguments:
      -h, --help            show this help message and exit
      --single              creates a single stand-alone mongod instance
      --replicaset          creates replica set with several mongod instances
      --nodes NUM           adds NUM data nodes to replica set (requires
                            --replicaset)
      --arbiter             adds arbiter to replica set (requires --replicaset)
      --name NAME           name for replica set
      --sharded [NAME [NAME ...]]
                            creates a sharded setup consisting of several singles
                            or replica sets
      --config NUM          adds NUM config servers to sharded setup (NUM must be
                            1 or 3, requires --sharded)
      --port PORT           port for mongod, start of port range in case of
                            replica set or shards
      --verbose             outputs information about the launch


<hr>

mlogmerge
---------

#### Description

A script that takes log files as input and merges them by date/time. 
	
	usage: mlogmerge logfiles [-h | --help] [--label LABELS] [--pos POS]

	positional arguments: 
	  logfiles              list of logfiles to merge

	optional arguments:
	  -h, --help            show this help message and exit
	  --labels LABELS       either one of 'enum' (default), 'alpha', 
							'filename', 'none' or a list of labels (must
							match number of logfiles)
	  --pos POS             position where label is printed in line. 
							either a number (default: 0) or 'eol'


<hr>

mplotqueries
------------

#### Additional dependencies
- NumPy
- matplotlib

See the [INSTALL.md](https://github.com/rueckstiess/mtools/blob/master/INSTALL.md) file for installation instructions of these dependencies.

#### Description

A script to plot query durations in a logfile (requires numpy and matplotlib modules).
	
    usage: mplotqueries filename [-h] [--ns [NS [NS ...]]] [--exclude-ns [NS [NS ...]]]
               
	positional arguments: 
	  filename              log file to plot

	optional arguments:
	  -h, --help                   show this help message and exit
      --ns [NS [NS ...]]           namespaces to include in the plot (default is all)
      --exclude-ns [NS [NS ...]]   namespaces to exclude from the plot


<hr> 

mlogfilter
----------

#### Description

A filter script to reduce the amount of information from MongoDB log files.  
Currently, the script supports filtering by time (from - to), to only show 
slow queries, to filter by arbitrary keywords, or any combination
of these filters.


	usage: mlogfilter logfile [-h] [--from FROM] [--to TO] [--word WORDS] [--slow]
						 
	positional arguments:
	  logfile               logfile to parse

	optional arguments:
	  -h, --help            show this help message and exit
	  --from FROM           output starting at FROM
	  --to TO               output up to TO
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
