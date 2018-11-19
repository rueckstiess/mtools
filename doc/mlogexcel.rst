.. _mlogexcel:

=========
mlogexcel
=========

**mlogexcel** is a script to parse log files and dump them into an Excel file.
The log message fields are organized as columns.  The Excel file can be used
later for analysis or simply more convenient visual inspection.


Usage
~~~~~

.. code-block:: bash

   mlogexcel [-h] [--version] logfile
             [-o|--out] [--pattern]

**mlogexcel** can also be used with shell pipe syntax:

.. code-block:: bash

   mlogfilter logfile [parameters] | mlogexcel


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

Output
---------
``-o, --out``
   output filename.  Default is <original logfile>.xlsx

``--actual``
   output the original JSON instead of patterns for query text, sort keys,
   and planSummary
