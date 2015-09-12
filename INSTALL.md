Installation Instructions for mtools
====================================

### Python

You need to have a version of Python installed in order to use mtools. Python
2.6.x and Python 2.7.x are currently supported. To check your Python version,
run `python --version` on the command line. Python 3.x is currently not supported.

### mtools Installation

#### Installation with `pip`

The easiest way to install mtools is via `pip`. From the command line, run:

    pip install mtools

You need to have `pip` installed for this to work. If you don't have `pip` installed yet,
try `sudo easy_install pip` from the command line first, or follow the instructions provided on the
[pip installation page](http://www.pip-installer.org/en/latest/installing.html#using-the-installer).

Depending on your user rights, it may complain about not having permissions to install the module.
In that case, you need to add `sudo` in front of the command.

Note that some mtools scripts have [additional dependencies](https://github.com/rueckstiess/mtools/blob/master/INSTALL.md#additional-dependencies), listed below.

##### Issues with XCode 5.1 (clang 3.4)

If you install mtools prior to version 1.1.4 on OS X Mavericks with the latest update to clang 3.4, you may see installation errors due to the compilation of psutil's C-extension. See github [issue #203](https://github.com/rueckstiess/mtools/issues/203) for details and a work-around. The issue is fixed in version 1.1.5 and above.

#### Installation Walk-Through for Ubuntu Desktop 12.04

Follow [this tutorial](https://github.com/rueckstiess/mtools/wiki/mtools-Installation-on-Ubuntu-12.04) for step-by-step instructions to install mtools and all dependencies on Ubuntu Desktop 12.04 64-bit.

#### Installation From Source

If pip is not available and you want to install mtools from source, you can get the source code
by cloning the [mtools github repository](https://github.com/rueckstiess/mtools):

    git clone git://github.com/rueckstiess/mtools.git

Or download the tarball from <https://pypi.python.org/pypi/mtools> and extract it with

    tar xzvf mtools-<version>.tar.gz

Then `cd` into the mtools directory and run

    sudo python setup.py install

This will install mtools into your Python's site-packages folder, create links to the
scripts and set everything up. You should now be able to use all the scripts directly
from the command line.

If you want to contribute to mtools development or test beta and release candidate versions,
you should install mtools in "development mode". Instead of the last command, run

    sudo python setup.py develop

More information about switching to development mode can be found on the page [mtools Development Mode](https://github.com/rueckstiess/mtools/wiki/mtools-Development-Mode).

Except for external dependencies like pymongo (required for mlaunch) or matplotlib (required
for mplotqueries), mtools is now setup and ready to be used.



### Additional Dependencies

#### psutil

*required for mlaunch*

mlaunch can now kill processes or send other signals. For this feature, the `psutil`
module is required. It will install automatically when mtools is installed with `pip`.

To install `psutil` manually, you can run

    pip install psutil


#### pymongo

*required for mlaunch*

pymongo is MongoDB's official Python driver. Once you have installed `pip`, you can install
pymongo easily by running

    pip install pymongo

Depending on your user rights, it may complain about not having permissions to install the module.
In that case, you need to add `sudo` in front of the command. Support for pymongo 3.x was added
in version 1.1.9.


#### Matplotlib

*required for mplotqueries*

[matplotlib](http://matplotlib.org/) is a python 2D plotting library which produces
figures and graphs in a variety of formats and interactive environments across platforms.

Installation instructions for matplotlib can be found under the [matplotlib Installation Guide](https://github.com/rueckstiess/mtools/wiki/matplotlib-Installation-Guide) page.


#### NumPy

*required for matplotlib (in mplotqueries)*

[NumPy](http://numpy.scipy.org/) is a Python module for scientific computing and numerical calculations. Version 1.8.0 or higher is required for mtools. Try installing NumPy with pip, by doing:

    pip install numpy

Depending on your user rights, it may complain about not having permissions to install the module.
In that case, you need to add `sudo` in front of the command.

If this doesn't work for you, you can install a binary or install from source code. Refer to the
installation instructions on the [NumPy](http://numpy.scipy.org/) page.


#### All Requirements

The full list of requirements (some of which are already included in the Python standard library) can be found in the [requirements.txt](./requirements.txt) file.
