Changes to mtools
=================

#### version 1.0.1

  * fixed timezone bug in mlogmerge (#24)
  * allow for multiple mongos in mlaunch with `--mongos` NUM parameter (#30)
  * mlaunch can now take any additional arguments (like `-vvv`) and pass it on to the mongod/s instances (#31)
  * all scripts now have --version flag (inherited from BaseCmdLineTool) (#34)
  * added `--fast` option to mlogfilter (#37)
  * mlogvis title added and legend height determined automatically (#45)
  * mlaunch now checks if port is available before trying to start and exits if port is already in use (#43)
  * fixed bug in logline parsing when detecting duration at the end of a line
  * changed `--log` to `--logscale` argument for mplotqueries to avoid confusion with "log" files
  * restructured tools to derive from base class `BaseCmdLineTool` or LogFileTool
  * added [Contributing](tutorials/contributing.md) page under the tutorials section

#### version 1.0.0

This is the first version of mtools that has a version number. Some significant changes to its unnumbered predecessor are:

  * installable via pip
  * directory re-organization: All tools are now located under `mtools/mtools/`. This makes for easier `PYTHONPATH` integration, which will now have to point to the actual mtools directory, and not to the parent directory anymore. This is more in line with other Python projects.
  * `mlogvis` tool added: a simplified version of `mplotqueries` that doesn't require `matplotlib` dependency. Instead, it will run in a browser window, using [d3.js](http://www.d3js.org/) for visualization. `mlogvis` is currently in BETA state.
  * introduced versioning: The version is stored in mtools/version.py and can be accessed programmatically from a Python shell with

        import mtools
        mtools.__version__

