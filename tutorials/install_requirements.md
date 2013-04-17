# How to Install Dependencies 

While most mtools scripts only require Python, mplotqueries has some more dependencies which in some cases have proven tricky to install on Mac OS X.

Here are some walk-through instructions to install all the necessary dependencies for Mac OS X Mountain Lion. For completeness, the instructions include installation of pymongo, which is only necessary for mlaunch.

### Install Command Line Tools


* Website: http://connect.apple.com
* Login with Apple Developer ID
* Download Command Line Tools for Mac OS X Mountain Lion and install


### Install pip

    sudo easy_install pip



### Install SciPySuperpack 

See also: http://sergeykarayev.com/work/2012-08-08/setting-up-mountain-lion/

    mkdir ~/local && cd ~/local
    git clone git://github.com/fonnesbeck/ScipySuperpack.git
    cd ScipySuperpack
    sh install_superpack.sh
    
verify by running `python` at the command line and typing `import matplotlib`. No error means it is installed.


### Install pymongo (for mlaunch)

    sudo pip install pymongo



### Install mtools

Website: https://github.com/rueckstiess/mtools

    cd /path/to/github/repos
    git clone git://github.com/rueckstiess/mtools.git

add to ~/.bashrc:

    export PYTHONPATH=$PYTHONPATH:/path/to/github/repos      (the parent dir of mtools)
    export PATH=$PATH:/path/to/github/repos/mtools/scripts

