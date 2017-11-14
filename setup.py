import sys
import platform
import re

# try importing from setuptools, if unavailable use distutils.core
try:
    from setuptools import setup, find_packages

    # test for 2.7-included packages, add to requirements if not available
    install_requires = []

    # Additional dependencies from requirements.txt that should be installed for
    # full mtools feature support. These are optional dependencies to simplify
    # the default install experience, particularly where a build toolchain is
    # required.
    extras_requires = {
        "all": ['matplotlib>=1.3.1', 'numpy>=1.8.0', 'pymongo>=3.3'],
        "mlaunch": ['pymongo>=3.3'],
        "mlogfilter": [],
        "mloginfo": ['numpy>=1.8.0'],
        "mlogvis": [],
        "mplotqueries": ['matplotlib>=1.3.1', 'numpy>=1.8.0'],
    }

    try:
        import argparse
    except ImportError:
        install_requires.append('argparse')

    try:
        from collections import OrderedDict
    except ImportError:
        install_requires.append('ordereddict')
        test_requires.append('ordereddict')

    # add dateutil if not installed already
    try:
        import dateutil
    except ImportError:
        install_requires.append('python-dateutil==2.2')
        test_requires.append('python-dateutil==2.2')

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
        'mtools.mgenerate',
        'mtools.test',
        'mtools.util',
        'mtools.mlogfilter.filters',
        'mtools.mplotqueries.plottypes',
        'mtools.mloginfo.sections']
    kws = {}

# import version from mtools/version.py
with open('mtools/version.py') as f:
    exec(f.read())

# read README.rst for long_description content
with open('README.rst') as f:
    long_description = f.read()

if sys.platform == 'darwin' and 'clang' in platform.python_compiler().lower():
    from distutils.sysconfig import get_config_vars
    res = get_config_vars()
    for key in ('CFLAGS', 'PY_CFLAGS'):
        if key in res:
            flags = res[key]
            flags = re.sub('-mno-fused-madd', '', flags)
            res[key] = flags

setup(
    name='mtools',
    version=__version__,
    packages=packages,
    package_data = {
        'mtools': ['data/log2code.pickle', 'data/index.html'],
    },
    entry_points={
        "console_scripts": [
            "mgenerate=mtools.mgenerate.mgenerate:main",
            "mlaunch=mtools.mlaunch.mlaunch:main",
            "mlogfilter=mtools.mlogfilter.mlogfilter:main",
            "mloginfo=mtools.mloginfo.mloginfo:main",
            "mlogvis=mtools.mlogvis.mlogvis:main",
            "mplotqueries=mtools.mplotqueries.mplotqueries:main"
        ],
    },
    author='Thomas Rueckstiess',
    author_email='thomas@rueckstiess.net',
    url='https://github.com/rueckstiess/mtools',
    description='Useful scripts to parse and visualize MongoDB log files, launch test environments, and reproduce issues.',
    long_description=long_description,
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Database',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='MongoDB logs testing',
    extras_require=extras_requires,
    **kws
)
