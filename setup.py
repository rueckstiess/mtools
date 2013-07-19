# nose tests require multiprocessing package, see 
# https://groups.google.com/forum/#!msg/nose-users/fnJ-kAUbYHQ/_UsLN786ygcJ
import multiprocessing

# try importing from setuptools, if unavailable use distutils.core
try:
    from setuptools import setup, find_packages

    # test for 2.7-included packages, add to requirements if not available
    install_requires = []
    try:
        import argparse
    except ImportError:
        install_requires.append('argparse')

    try:
        from collections import OrderedDict
    except ImportError:
        install_requires.append('ordereddict')

    kws = {'install_requires': install_requires}

except ImportError:
    from distutils.core import setup
    kws = {}

# import version from mtools/version.py
exec(open('mtools/version.py').read())

# read README.md for long_description content
with open('README.md') as f:
    long_description = f.read()

setup(
    name='mtools', 
    version=__version__,
    packages=find_packages(),
    package_data = {
        'mtools': ['data/log2code.pickle', 'data/index.html'],
    },
    scripts=['scripts/mlaunch','scripts/mlog2json','scripts/mlogdistinct',
        'scripts/mlogfilter','scripts/mlogmerge','scripts/mlogversion',
        'scripts/mlogvis','scripts/mplotqueries'],
    author='Thomas Rueckstiess',
    author_email='thomas@rueckstiess.net',
    url='https://github.com/rueckstiess/mtools',
    description='Useful scripts to parse and visualize MongoDB log files.',
    long_description=long_description,
    tests_require=['nose>=1.0', 'psutil', 'pymongo>=2.4'],
    test_suite = 'nose.collector',
    **kws
)
