# How to Install Dependencies 

While most mtools scripts only require Python, mplotqueries has some more dependencies which in some cases have proven tricky to install on Mac OS X.

Here are some walk-through instructions to install all the necessary dependencies for Mac OS X Mountain Lion.

* Install Command Line Tools

Website: http://connect.apple.com
Login with Apple Developer ID
Download Command Line Tools for Mac OS X Mountain Lion and install

If you don't have an Apple Developer ID, I've also shared the file on my Dropbox. Access from:



* Install m

Website: https://github.com/aheckmann/m
git clone git://github.com/aheccd ..
kmann/m.git && cd m && make install
Install some mongodb versions (2.2.x, 2.4.x)...



* Install pip

sudo easy_install pip



* Install SciPySuperpack  (this will take a while to clone)

See also: http://sergeykarayev.com/work/2012-08-08/setting-up-mountain-lion/

mkdir ~/local && cd ~/local
git clone git://github.com/fonnesbeck/ScipySuperpack.git
cd ScipySuperpack
sh install_superpack.sh
verify by running "python" and typing "import matplotlib". No error means it is installed.



* Install pymongo

sudo pip install pymongo



* Install mtools

Website: https://github.com/rueckstiess/mtools

cd /path/to/github/repos
git clone git://github.com/rueckstiess/mtools.git

add to ~/.bashrc:
  export PYTHONPATH=$PYTHONPATH:/path/to/github/repos      (the parent dir of mtools)
	export PATH=$PATH:/path/to/github/repos/mtools/scripts

