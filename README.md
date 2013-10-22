# mtools

[![PyPI version](https://badge.fury.io/py/mtools.png)](http://badge.fury.io/py/mtools)

**mtools** is a collection of helper scripts to parse and filter MongoDB log files (mongod, mongos), visualize log files and quickly set up complex MongoDB test environments on a local machine.


### What's in the box?

The following tools are in the mtools collection:

[mlogfilter](./wiki/mlogfilter) <br>
slices log files by time, merges log files, filters slow queries, finds table scans, shortens log lines, filters by other atributes, convert to JSON

[mloginfo](./wiki/mloginfo) <br>
returns info about log file, like start and end time, version, binary, special sections like restarts, connections, distinct view.

[mplotqueries](./wiki/mplotqueries) <br>
visualize logfiles with different types of plots (requires matplotlib)

[mlogvis](./wiki/mlogvis) <br>
creates a self-contained html file that shows an interactive visualization in a web browser (as an alternative to mplotqueries)

[mlaunch](./wiki/mlaunch) <br>
a script to quickly spin up local test environments, including replica sets and sharded systems (requires pymongo)



Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only make
use the standard packages shipped with Python version 2.6.x and 2.7.x, and should run out of the box.

Some of the tools have additional dependencies, which are listed under the 
specific tool's section. See the [INSTALL.md](./INSTALL.md) file for installation 
instructions for these modules.


Recent Changes
--------------

The current version of mtools is 1.1. See [CHANGES.md](./CHANGES.md) for a list of recent changes from previous versions of mtools.


Contribute to mtools
--------------------
If you'd like to contribute to mtools, please read the [contributor page](tutorials/contributing.md) for instructions.


Disclaimer
----------

This software is not supported by [MongoDB, Inc.](http://www.mongodb.com) under any of their commercial support subscriptions or otherwise. Any usage of mtools is at your own risk. 
Bug reports, feature requests and questions can be posted in the [Issues](https://github.com/rueckstiess/mtools/issues?state=open) section here on github. 


