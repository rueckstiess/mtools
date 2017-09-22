======
mtools
======

|PyPI version| |Build Status| |Python 27|

**mtools** is a collection of helper scripts to parse, filter, and visualize
MongoDB log files (``mongod``, ``mongos``). mtools also includes ``mlaunch``, a
utility to quickly set up complex MongoDB test environments on a local machine.

.. figure:: ./mtools.png
   :alt: mtools box

   mtools box

What's in the box?
------------------

The following tools are in the mtools collection:

`mlogfilter <https://github.com/rueckstiess/mtools/wiki/mlogfilter>`__ slices
log files by time, merges log files, filters slow queries, finds table scans,
shortens log lines, filters by other atributes, convert to JSON

`mloginfo <https://github.com/rueckstiess/mtools/wiki/mloginfo>`__ returns info
about log file, like start and end time, version, binary, special sections like
restarts, connections, distinct view

`mplotqueries <https://github.com/rueckstiess/mtools/wiki/mplotqueries>`__
visualize logfiles with different types of plots (requires matplotlib)

`mlogvis <https://github.com/rueckstiess/mtools/wiki/mlogvis>`__ creates a
self-contained html file that shows an interactive visualization in a web
browser (as an alternative to mplotqueries)

`mlaunch <https://github.com/rueckstiess/mtools/wiki/mlaunch>`__ a script to
quickly spin up local test environments, including replica sets and sharded
systems (requires pymongo)

You can find the manual and many usage examples on the `mtools wiki pages
<https://github.com/rueckstiess/mtools/wiki>`__.

Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only use the
standard packages shipped with Python version 2.7.x.

mtools is not currently compatible with Python 3.

Some of the tools have additional dependencies, which are listed under the
specific tool's section. See the `INSTALL.md <./INSTALL.md>`__ file for
installation instructions for these modules.

The mtools utilities are only tested with currently supported (non End-of-Life)
versions of the MongoDB server. As of September 2017, that includes MongoDB 3.0
or newer.

Recent Changes
--------------

The current version of mtools is 1.3.0. See `CHANGES.md <./CHANGES.md>`__ for a
list of recent changes from previous versions of mtools.

Contribute to mtools
--------------------

If you'd like to contribute to mtools, please read the `contributor page
<https://github.com/rueckstiess/mtools/wiki/Development:-contributing-to-mtools>`__
for instructions.

Disclaimer
----------

This software is not supported by `MongoDB, Inc. <https://www.mongodb.com>`__
under any of their commercial support subscriptions or otherwise. Any usage of
mtools is at your own risk. Bug reports, feature requests and questions can be
posted in the `Issues
<https://github.com/rueckstiess/mtools/issues?state=open>`__ section here on
github.

.. |PyPI version| image:: https://img.shields.io/pypi/v/mtools.svg
   :target: https://pypi.python.org/pypi/mtools/
.. |Build Status| image:: https://img.shields.io/travis/rueckstiess/mtools/master.svg
   :target: https://travis-ci.org/rueckstiess/mtools
.. |Python 27| image:: https://img.shields.io/badge/Python-2.7-brightgreen.svg?style=flat
   :target: http://python.org