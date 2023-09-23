======
mtools
======

|PyPI version| |PyPI pyversions| |PyPI license|

**mtools** is a collection of helper scripts to parse, filter, and visualize
MongoDB log files (``mongod``, ``mongos``). mtools also includes ``mlaunch``, a
utility to quickly set up complex MongoDB test environments on a local machine,
and ``mtransfer``, a tool for transferring databases between MongoDB instances.

.. figure:: https://raw.githubusercontent.com/rueckstiess/mtools/develop/mtools.png
   :alt: mtools box

What's in the box?
------------------

The following tools are in the mtools collection:

`mlogfilter <https://rueckstiess.github.io/mtools/mlogfilter.html>`__
   slices log files by time, merges log files, filters slow queries, finds
   table scans, shortens log lines, filters by other attributes, convert to
   JSON

`mloginfo <https://rueckstiess.github.io/mtools/mloginfo.html>`__
   returns info about log file, like start and end time, version, binary,
   special sections like restarts, connections, distinct view
   (requires ``numpy``)

`mplotqueries <https://rueckstiess.github.io/mtools/mplotqueries.html>`__
   visualize log files with different types of plots (requires ``matplotlib``)

`mlaunch <https://rueckstiess.github.io/mtools/mlaunch.html>`__
   a script to quickly spin up local test environments, including replica sets
   and sharded systems (requires ``pymongo``, ``psutil``, ``packaging``)

`mtransfer <https://rueckstiess.github.io/mtools/mtransfer.html>`__
   an experimental script to transfer databases between MongoDB instances by
   copying WiredTiger data files (requires ``pymongo`` and ``wiredtiger``)

For more information, see the `mtools documentation
<https://rueckstiess.github.io/mtools>`__.

Requirements and Installation Instructions
------------------------------------------

The mtools collection is written in Python, and most of the tools only use the
standard packages shipped with Python. The tools are currently tested with
Python 3.8, 3.9, 3.10, and 3.11.

Some of the tools have additional dependencies, which are listed under the
specific tool's section. See the `installation instructions
<https://rueckstiess.github.io/mtools/install.html>`__ for more information.

The mtools suite is only tested with
`actively supported <https://www.mongodb.com/support-policy/lifecycles>`
(non End-of-Life) versions of the MongoDB server. As of September 2023,
that includes MongoDB 4.4 or newer.

Recent Changes
--------------

See `Changes to mtools <https://rueckstiess.github.io/mtools/changelog.html>`__
for a list of changes from previous versions of mtools.

Contribute to mtools
--------------------

If you'd like to contribute to mtools, please read the `contributor page
<https://rueckstiess.github.io/mtools/contributing.html>`__ for instructions.

Disclaimer
----------

This software is not supported by `MongoDB, Inc. <https://www.mongodb.com>`__
under any of their commercial support subscriptions or otherwise. Any usage of
mtools is at your own risk. Bug reports, feature requests and questions can be
posted in the `Issues
<https://github.com/rueckstiess/mtools/issues?state=open>`__ section on GitHub.

.. |PyPI version| image:: https://img.shields.io/pypi/v/mtools.svg
   :target: https://pypi.python.org/pypi/mtools/
.. |PyPI pyversions| image:: https://img.shields.io/pypi/pyversions/mtools.svg
   :target: https://pypi.python.org/pypi/mtools/
.. |PyPI license| image:: https://img.shields.io/pypi/l/mtools.svg
   :target: https://pypi.python.org/pypi/mtools/
