============
Installation
============

The mtools collection is written in Python, and most of the tools only use the
standard packages shipped with Python. The tools are currently tested with
Python 3.7, 3.8, 3.9, 3.10, and 3.11.

Some of the tools have additional dependencies, which are listed under the
specific tool's section.

The mtools suite is only tested with actively supported (non End-of-Life)
versions of the MongoDB server. As of November 2022, that includes
MongoDB 4.2 or newer.

Prerequisites
~~~~~~~~~~~~~

Python
   You need to have Python 3.7, 3.8, 3.9, 3.10, or 3.11 installed in order to
   use mtools. Other versions of Python are not currently supported or tested.

   To check your Python version, run ``python --version`` on the command line.

Installation with pip3
~~~~~~~~~~~~~~~~~~~~~~

The easiest way to install mtools is via ``pip3``. From the command line, run:

.. code-block:: bash

   pip3 install mtools

Some mtools scripts have additional `dependencies`_. To install all optional
dependencies use:

.. code-block:: bash

   pip3 install 'mtools[all]'

You need to have Python 3.7 or newer installed. ``pip3`` should be included as
part of the default install for supported versions of Python 3.

Depending on your user rights, ``pip3`` may complain about not having
permissions to install into the system directory.

In that case, you either need to add ``sudo`` in front of the ``pip3`` command
to install into a system directory, or append ``--user`` to install into your
home directory.

Installation from source
~~~~~~~~~~~~~~~~~~~~~~~~

If ``pip3`` is not available and you want to install mtools from source, you can
get the source code by cloning the `mtools github repository
<https://github.com/rueckstiess/mtools>`__:

.. code-block:: bash

   git clone git://github.com/rueckstiess/mtools.git

Or download the tarball from `PyPI <https://pypi.python.org/pypi/mtools>`__ and
extract it with:

.. code-block:: bash

   tar xzvf mtools-<version>.tar.gz

Then ``cd`` into the mtools directory and run:

.. code-block:: bash

   sudo python setup.py install

This will install mtools into your Python's site-packages folder, create links
to the scripts and set everything up. You should now be able to use all the
scripts directly from the command line.

.. _dependencies:

Dependencies
~~~~~~~~~~~~

The full list of requirements (some of which are already included in the Python
standard library) can be found in the `requirements.txt
<https://github.com/rueckstiess/mtools/blob/develop/requirements.txt>`__ file.

To install all dependencies for full feature support, run:

.. code-block:: bash

   pip3 install 'mtools[all]'

To install dependencies for a subset of mtools utilities, specify one or more
script names as a comma-separated list:

.. code-block:: bash

   pip3 install 'mtools[mlaunch,mloginfo]'

psutil
------

*required for mlaunch*

mlaunch uses ``psutil`` to manage starting, stopping, and finding MongoDB
processes.

pymongo
-------

*required for mlaunch and mtransfer*

`pymongo <https://www.mongodb.com/docs/drivers/pymongo/#installation>`__
is MongoDB's official Python driver. ``mlaunch`` uses this to configure
and query local MongoDB deployments.

matplotlib
----------

*required for mplotqueries*

`matplotlib <https://matplotlib.org/>`__ is a python 2D plotting library which
produces figures and graphs in a variety of formats and interactive
environments across platforms.

numpy
-----

*required for matplotlib (in mplotqueries)*

`numpy <https://numpy.scipy.org/>`__ is a Python module for scientific
computing and numerical calculations.

wiredtiger
----------

*required for mtransfer*

`WiredTiger <https://github.com/wiredtiger/wiredtiger/>`__ is the default
storage engine for MongoDB.
