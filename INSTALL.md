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

Except for external dependencies like pymongo (required for mlaunch) or matplotlib (required
for mplotqueries), mtools is now setup and ready to be used.


### Additional Dependencies

#### pymongo

*required for mlaunch*

pymongo is MongoDB's official Python driver. Once you have installed `pip`, you can install 
pymongo easily by running

    pip install pymongo

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to add `sudo` in front of the command.


#### Matplotlib

*required for mplotqueries*

[matplotlib](http://matplotlib.org/) is a python 2D plotting library which produces 
figures and graphs in a variety of formats and interactive environments across platforms.

Try installing matplotlib with `pip`, by doing:

    pip install matplotlib

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to add `sudo` in front of the command.

If this doesn't work for you, there are a number of alternative ways to install matplotlib. Refer
to the [matplotlib installation page](http://matplotlib.org/users/installing.html) for additional
information.


#### NumPy

*required for matplotlib (in mplotqueries)*

[NumPy](http://numpy.scipy.org/) is a Python module for scientific computing and numerical calculations.
Try installing NumPy with pip, by doing:

    pip install numpy

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to add `sudo` in front of the command.

If this doesn't work for you, you can install a binary or install from source code. Refer to the 
installation instructions on the [NumPy](http://numpy.scipy.org/) page.


