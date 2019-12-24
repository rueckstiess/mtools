.. _mtransfer:

=========
mtransfer
=========

``mtransfer`` allows WiredTiger databases to be exported from one MongoDB
instance and imported into another.


Caveats
~~~~~~~

The ``mtransfer`` script is EXPERIMENTAL and has a number of important usage caveats:

- MongoDB must be started with the ``--directoryperdb`` flag.
- ``mtransfer`` does not work with sharding, the encrypted storage engine, or
  MMAPv1 data files.
- To export or import a database, MongoDB must not be running using either the
  source or destination database paths.
- A database must be imported to all nodes in a replica set or query results
  will be inconsistent.
- A database cannot be imported to any node in the replica set it was exported
  from. Collections have unique identifiers, and this would violate that uniqueness.
- ``mtransfer`` currently only supports database files compressed with the
  default `snappy` library.

While there are some sanity checks built into the script, manipulating MongoDB
files directly is inherently dangerous. Take care to test and backup your data.

Installation
~~~~~~~~~~~~

The ``mtransfer`` script requires the
`wiredtiger Python library <https://pypi.org/project/wiredtiger/>`__
which is currently not installed by default with ``mtools``.

The ``wiredtiger`` library can be installed via ``pip`` or built from source,
but in either case requires:

- A C compiler.
- The ``snappy`` and ``zlib`` development packages installed.

To install via ``pip`` use either of:

.. code-block:: bash

   pip install mtools[mtransfer]

.. code-block:: bash

   pip install wiredtiger

If you are encountering errors using or installing the ``wiredtiger`` module
via `pip`, you may need to `Build and install WiredTiger from source
<http://source.wiredtiger.com/develop/build-posix.html>`__.

Usage
~~~~~

.. code-block:: bash

  mtransfer [-h] [--version] [--verbose] [--dbpath DBPATH]
                    {export,import} database

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

Verbosity
---------
``--verbose``
   shows extra information

Commands
~~~~~~~~

``mtransfer`` reads or writes the data files in a MongoDB instance
using the WiredTiger storage engine.

Database Path
-------------
``--dbpath path`` the path to the MongoDB database files (defaults to
the current working directory where the script is run).

Command
-------
``export``
creates a file ``mtransfer.bson`` in the specified database directory.
This must be copied along with the other files in the directory to the
destination server(s).

``import`` reads the ``mtransfer.bson`` file from the specified database
directory and updates MongoDB's metadata to include the database.

Database
---------
The name of the database to export / import.  The MongoDB database name
must match the directory name on disk for the export, and the MongoDB
database name will be set to the directory name for the import.

Example
~~~~~~~

On the origin
-------------

Before starting, ensure MongoDB is not running.

.. code-block:: bash
  
  cd /from/dbpath
  # Create 'olddb/mtransfer.bson' with exported metadata
  mtransfer export olddb
  # Copy the database files to the destination
  rsync -av olddb destination:/to/dbpath

On the destination
------------------

Before starting, ensure MongoDB is not running.

.. code-block:: bash
  
  cd /to/dbpath
  # Rename the database directory
  mv olddb newdb
  # Import the database (with the new name)
  mtransfer import newdb

Disclaimer
~~~~~~~~~~

This software is not supported by `MongoDB, Inc. <https://www.mongodb.com>`__
under any of their commercial support subscriptions or otherwise. Any usage of
mtools is at your own risk. Bug reports, feature requests and questions can be
posted in the `Issues
<https://github.com/rueckstiess/mtools/issues?state=open>`__ section on GitHub.