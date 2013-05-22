Installation Instructions for mtools
====================================


#### Python
You will need to have a version of Python installed for all the scripts
below, 2.7.x is recommended. 2.6.x will work but you need to install the `argparse` 
module separately (you can use `pip` to install it, see below). To check your
Python version, run `python --version` on the command line.

Python 3.x is currently not supported.


#### mtools installation

Clone the [mtools github repository](https://github.com/rueckstiess/mtools) into a 
directory of your choice:

	cd /path/to/github/repos
    git clone git://github.com/rueckstiess/mtools.git

This will create a sub-folder `mtools` under the `/path/to/github/repos/` folder 
and check out the code there. You need to add the `/path/to/github/repos/mtools` folder to
your `PYTHONPATH` environment variable. If you use the _bash_ shell, you can do so by 
adding a line

    export PYTHONPATH=$PYTHONPATH:/path/to/github/repos/mtools/

to your `.bashrc` script. Other shells may have a different syntax.


#### Command style usage

While you can execute each of the scripts with `python script.py` ("script.py" being a
placeholder for the real script name), it is convenient to use the symbolic links
that are located in the `mtools/scripts/` subfolder.

Add the `mtools/scripts/` subfolder to your `PATH` environment variable, if you 
want to use the scripts from anywhere in the shell. If you use the _bash_ shell, 
you can do so by adding a line
    
    export PATH=$PATH:/path/to/github/repos/mtools/scripts

to your `.bashrc` script. Other shells may have a different syntax.


#### pip

Some of the additional requirements can be installed easily with the `pip` tool, Python's
package installer. To install `pip`, follow the instructions provided on the 
[pip installation page](http://www.pip-installer.org/en/latest/installing.html#using-the-installer).


#### argparse

If you run Python version 2.6.x, the `argparse` module is not included in the standard library and
you need to install it manually. You can do so with

    pip install argparse

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to precede the command with a `sudo`.


#### pymongo

*required for mlaunch*

pymongo is MongoDB's official Python driver. Once you have installed `pip`, you can install 
pymongo easily by running

    pip install pymongo

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to precede the command with a `sudo`.


#### Matplotlib

*required for mplotqueries*

[matplotlib](http://matplotlib.org/) is a python 2D plotting library which produces 
figures and graphs in a variety of formats and interactive environments across platforms.

Try installing matplotlib with `pip`, by doing:

    pip install matplotlib

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to precede the command with a `sudo`.

If this doesn't work for you, there are a number of alternative ways to install matplotlib. Refer
to the [matplotlib installation page](http://matplotlib.org/users/installing.html) for additional
information.


#### NumPy

*required for matplotlib (in mplotqueries)*

[NumPy](http://numpy.scipy.org/) is a Python module for scientific computing and numerical calculations.
Try installing NumPy with pip, by doing:

    pip install numpy

Depending on your user rights, it may complain about not having permissions to install the module. 
In that case, you need to precede the command with a `sudo`.

If this doesn't work for you, you can install a binary or install from source code. Refer to the 
installation instructions on the [NumPy](http://numpy.scipy.org/) page.


