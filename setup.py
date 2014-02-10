# nose tests require multiprocessing package, see 
# https://groups.google.com/forum/#!msg/nose-users/fnJ-kAUbYHQ/_UsLN786ygcJ
import multiprocessing

# try importing from setuptools, if unavailable use distutils.core
try:
    from setuptools import setup, find_packages

    # test for 2.7-included packages, add to requirements if not available
    install_requires = ['psutil']
    try:
        import argparse
    except ImportError:
        install_requires.append('argparse')

    try:
        from collections import OrderedDict
    except ImportError:
        install_requires.append('ordereddict')

    # add dateutil if not installed already
    try: 
        import dateutil
    except ImportError:
        install_requires.append('python-dateutil')

    packages = find_packages()
    kws = {'install_requires': install_requires}

except ImportError:
    from distutils.core import setup
    
    # find_packages not available in distutils, manually define packaging
    packages = ['mtools',
        'mtools.mlaunch',
        'mtools.mlogfilter',
        'mtools.mloginfo',        
        'mtools.mlogvis',
        'mtools.mplotqueries',
        'mtools.mlogversion',
        'mtools.mlogdistinct',
        'mtools.mlogmerge',
        'mtools.mlog2json',
        'mtools.mgenerate',
        'mtools.test',
        'mtools.util',
        'mtools.mlogfilter.filters',
        'mtools.mplotqueries.plottypes',
        'mtools.mloginfo.sections']
    kws = {}

# import version from mtools/version.py
exec(open('mtools/version.py').read())

# read README.md for long_description content
with open('README.md') as f:
    long_description = f.read()

setup(
    name='mtools', 
    version=__version__,
    packages=packages,
    package_data = {
        'mtools': ['data/log2code.pickle', 'data/index.html'],
    },
    scripts=['scripts/mlaunch', 'scripts/mlogfilter', 'scripts/mlogvis', 'scripts/mplotqueries', 'scripts/mloginfo', \
             'scripts/mlogversion', 'scripts/mlogmerge', 'scripts/mlog2json', 'scripts/mlogdistinct', 'scripts/mgenerate'],
    author='Thomas Rueckstiess',
    author_email='thomas@rueckstiess.net',
    url='https://github.com/rueckstiess/mtools',
    description='Useful scripts to parse and visualize MongoDB log files, launch test environments and reproduce issues.',
    long_description=long_description,
    tests_require=['nose>=1.0', 'psutil', 'pymongo>=2.4'],
    test_suite = 'nose.collector',
    **kws
)
