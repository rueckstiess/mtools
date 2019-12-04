======
mtools
======

|PyPI version| |Build Status| |Python 36| |Python 37| |Python 38|

**mtools** is a collection of helper scripts to parse, filter, and visualize
MongoDB log files (``mongod``, ``mongos``). mtools also includes ``mlaunch``, a
utility to quickly set up complex MongoDB test environments on a local machine,
and ``mtransfer``, a tool for transferring databases between MongoDB instances.

.. figure:: https://raw.githubusercontent.com/rueckstiess/mtools/develop/mtools.png
   :alt: mtools box

What's in the box?
------------------

The following tools are in the mtools collection:

`mlogfilter <http://rueckstiess.github.io/mtools/mlogfilter.html>`__
   slices log files by time, merges log files, filters slow queries, finds
   table scans, shortens log lines, filters by other attributes, convert to
   JSON

`mloginfo <http://rueckstiess.github.io/mtools/mloginfo.html>`__
   returns info about log file, like start and end time, version, binary,
   special sections like restarts, connections, distinct view

`mplotqueries <http://rueckstiess.github.io/mtools/mplotqueries.html>`__
   visualize log files with different types of plots (requires matplotlib)

`mlogvis <http://rueckstiess.github.io/mtools/mlogvis.html>`__
   creates a self-contained HTML file that shows an interactive visualization
   in a web browser (as an alternative to mplotqueries)

`mlaunch <http://rueckstiess.github.io/mtools/mlaunch.html>`__
   a script to quickly spin up local test environments, including replica sets
   and sharded systems (requires pymongo)

`mtransfer <http://rueckstiess.github.io/mtools/mtransfer.html>`__
   a script to transfer databases between MongoDB instances by copying data files.

For more information, see the `mtools documentation
<http://rueckstiess.github.io/mtools>`__.

Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only use the
standard packages shipped with Python. The tools are currently tested with
Python 3.6, 3.7, and 3.8.

Some of the tools have additional dependencies, which are listed under the
specific tool's section. See the `installation instructions
<http://rueckstiess.github.io/mtools/install.html>`__ for more information.

The mtools suite is only tested with actively supported (non End-of-Life)
versions of the MongoDB server. As of January 2020, that includes MongoDB 3.6
or newer.

Recent Changes
--------------

See `Changes to mtools <http://rueckstiess.github.io/mtools/changelog.html>`__
for a list of changes from previous versions of mtools.

Contribute to mtools
--------------------

If you'd like to contribute to mtools, please read the `contributor page
<http://rueckstiess.github.io/mtools/contributing.html>`__ for instructions.

Disclaimer
----------

This software is not supported by `MongoDB, Inc. <https://www.mongodb.com>`__
under any of their commercial support subscriptions or otherwise. Any usage of
mtools is at your own risk. Bug reports, feature requests and questions can be
posted in the `Issues
<https://github.com/rueckstiess/mtools/issues?state=open>`__ section on GitHub.

.. |PyPI version| image:: https://img.shields.io/pypi/v/mtools.svg
   :target: https://pypi.python.org/pypi/mtools/
.. |Build Status| image:: https://img.shields.io/travis/rueckstiess/mtools/master.svg
   :target: https://travis-ci.org/rueckstiess/mtools
.. |Python 36| image:: https://img.shields.io/badge/Python-3.6-brightgreen.svg?style=flat
   :target: http://python.org
.. |Python 37| image:: https://img.shields.io/badge/Python-3.7-brightgreen.svg?style=flat
   :target: http://python.org
.. |Python 38| image:: https://img.shields.io/badge/Python-3.8-brightgreen.svg?style=flat
   :target: http://python.org