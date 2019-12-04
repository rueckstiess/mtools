.. _mtransfer:

=========
mtransfer
=========

**mtransfer** allows databases to be exported from one MongoDB instance and
imported into another.


Caveats
~~~~~~~

**mtransfer** requires MongoDB by started with the ``--directoryperdb`` flag.
It does not work with sharding or the encrypted storage engine.
To export or import a database, MongoDB must not be running.
The database must be imported to all nodes in a replica set or query results
will be inconsistent. A database cannot be imported to any node in the replica
set it was exported from: collections have unique identifiers, and this would
violate that uniqueness.

While there are some sanity checks built into the script, manipulating MongoDB
files directly is inherently dangerous. Take care to test and backup your data.

Usage
~~~~~

.. code-block:: bash

  mtransfer.py [-h] [--version] [--verbose] [--dbpath DBPATH]
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

``mtransfer`` reads or writes the data files in a MongoDB instance.

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
