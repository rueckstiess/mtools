from setuptools import setup, find_packages

# import version from mtools/version.py
exec(open('mtools/version.py').read())

setup(
    name='mtools', 
    version=__version__,
    packages=find_packages(),
    package_data = {
        'mtools': ['data/logdb.pickle', 'data/index.html'],
    },
    scripts=['scripts/mlaunch','scripts/mlog2json','scripts/mlogdistinct',
        'scripts/mlogfilter','scripts/mlogmerge','scripts/mlogversion',
        'scripts/mlogvis','scripts/mplotqueries'],
    author='Thomas Rueckstiess',
    author_email='thomas@rueckstiess.net',
    url='https://github.com/rueckstiess/mtools',
    description='Useful scripts to parse and visualize MongoDB log files.',
)
