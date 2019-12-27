======
mtools
======

|PyPI version| |Build Status| |Python 36|

**mtools** is a collection of helper scripts to parse, filter, and visualize
MongoDB log files (``mongod``, ``mongos``). mtools also includes ``mlaunch``, a
utility to quickly set up complex MongoDB test environments on a local machine.

.. toctree::
   :hidden:

   install.rst
   mlaunch.rst
   mlogfilter.rst
   mloginfo.rst
   mlogvis.rst
   mplotqueries.rst
   contributing.rst
   changelog.rst


What's in the box?
~~~~~~~~~~~~~~~~~~

The following tools are in the mtools collection:

:ref:`mlogfilter`
   slices log files by time, merges log files, filters slow queries, finds
   table scans, shortens log lines, filters by other attributes, convert to
   JSON

:ref:`mloginfo`
   returns info about log file, like start and end time, version, binary,
   special sections like restarts, connections, distinct view

:ref:`mplotqueries`
   visualize log files with different types of plots (requires matplotlib)

:ref:`mlogvis`
   creates a self-contained HTML file that shows an interactive visualization
   in a web browser (as an alternative to mplotqueries)

:ref:`mlaunch`
   a script to spin up local test environments quickly, including replica sets
   and sharded systems (requires pymongo)

The `mtools source code <https://github.com/rueckstiess/mtools>`__ is available
on GitHub under an `Apache 2.0 license
<https://github.com/rueckstiess/mtools/blob/develop/LICENSE.md>`__.


Disclaimer
~~~~~~~~~~

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
