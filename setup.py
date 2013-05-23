from setuptools import setup, find_packages

setup(
    name='mtools', 
    version='1.0.0',
    packages=find_packages(),
    scripts=['scripts/mlaunch','scripts/mlog2json','scripts/mlogdistinct',
        'scripts/mlogfilter','scripts/mlogmerge','scripts/mlogversion',
        'scripts/mlogvis','scripts/mplotqueries'],
    include_package_data=True,
    author='Thomas Rueckstiess',
    author_email='thomas@rueckstiess.net',
    url='https://github.com/rueckstiess/mtools',
    description='Useful scripts to parse and visualize MongoDB log files.',
)