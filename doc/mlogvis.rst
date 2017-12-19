.. _mlogvis:

=======
mlogvis
=======

**mlogvis** is a script to visualize log files interactively in a browser,
using the `d3.js <https://d3js.org/>`__ Javascript visualization engine.
**mlogvis** provides an alternative to :ref:`mplotqueries` without the
matplotlib dependency, but currently only contains a sub-set of features of
mplotqueries.

The script will read a log file, process the data and write a self-contained
HTML file to the current working directory. It will then start open a browser
tab to display the file. The HTML file can also be sent to somebody and opened
by any modern browser (optimized for Google Chrome). An Internet connection is
required for dynamic loading of d3 Javascript library.

Usage
~~~~~

.. code-block:: bash

   mlogvis [-h] [--version] logfile

**mlogvis** can also be used with shell pipe syntax:

.. code-block:: bash

   mlogfilter logfile [parameters] | mlogvis


General Parameters
~~~~~~~~~~~~~~~~~~

Help
----
``-h, --help``
   shows the help text and exits.

Version
-------
``--version``
   shows the version number and exits.
