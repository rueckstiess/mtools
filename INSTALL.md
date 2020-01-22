Installation Instructions for mtools
====================================

### Python

You need to have Python 3.6 or newer installed in order to use mtools.
Older versions of Python are not supported.

To check your Python version, run `python --version` on the command line.

### mtools Installation

#### Installation with `pip3`

The easiest way to install mtools is via `pip3`. From the command line, run:

    pip3 install mtools

You need to have `pip3` installed for this to work. `pip3` should be included
as part of the default install for supported versions of Python 3.

Depending on your user rights, `pip3` may complain about not having permissions
to install into the system directory.

In that case, you either need to add `sudo` in front of the `pip3` command to
install into a system directory, or append `--user` to install into your home
directory.

Note that some mtools scripts have [additional dependencies](https://github.com/rueckstiess/mtools/blob/master/INSTALL.md#additional-dependencies) as listed below.

#### Installation from source

If `pip3` is not available and you want to install mtools from source, you can
get the source code by cloning the
[mtools github repository](https://github.com/rueckstiess/mtools):

    git clone git://github.com/rueckstiess/mtools.git

Or download the tarball from <https://pypi.python.org/pypi/mtools> and extract it with:

    tar xzvf mtools-<version>.tar.gz

Then `cd` into the mtools directory and run:

    sudo python setup.py install

This will install mtools into your Python's site-packages folder, create links to the
scripts and set everything up. You should now be able to use all the scripts directly
from the command line.

#### Development Mode source installation

If you want to contribute to mtools development or test beta and release candidate versions,
you should install mtools from a source checkout in "Development Mode" using either of:

 * `pip3` (recommended as a convenience for installing additional dependencies)
```
    sudo pip3 install -e'/path/to/cloned/repo[all]'
```

 * `setup.py`

```
    sudo python3 setup.py develop
```

More information about switching to Development Mode can be found on the page [mtools Development Mode](https://github.com/rueckstiess/mtools/wiki/Development-Mode-for-mtools).

### Additional dependencies

To install all additional dependencies for full feature support, run:

    pip3 install mtools[all]

To install dependencies for a subset of mtools utilities, specify one or more script names as a comma-separated list:

    pip3 install mtools[mlaunch,mloginfo]

#### psutil

*required for mlaunch*

mlaunch uses `psutil` to manage starting, stopping, and finding MongoDB processes.

#### pymongo

*required for mlaunch*

pymongo is MongoDB's official Python driver. `mlaunch` uses this to configure and query local MongoDB deployments.

#### Matplotlib

*required for mplotqueries*

[matplotlib](http://matplotlib.org/) is a python 2D plotting library which produces
figures and graphs in a variety of formats and interactive environments across platforms.

#### NumPy

*required for matplotlib (in mplotqueries)*

[NumPy](http://numpy.scipy.org/) is a Python module for scientific computing and numerical calculations.

### All requirements

The full list of requirements (some of which are already included in the Python standard library) can be found in the [requirements.txt](./requirements.txt) file.
