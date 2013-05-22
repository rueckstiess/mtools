Changes to mtools
=================

#### Version 1.0.0

This is the first version of mtools that has a version number. 

  * directory re-organization: All tools are now located under `mtools/mtools/`. This makes for easier `PYTHONPATH` integration, which will now have to point to the actual mtools directory, and not to the parent directory anymore. This is more in line with other Python projects.
  * `mlogvis` tool added: a simplified version of `mplotqueries` that doesn't require `matplotlib` dependency. Instead, it will run in a browser window, using [d3.js](http://www.d3js.org/) for visualization. `mlogvis` is currently in BETA state.
  * introduced versioning: The version can be accessed programmatically from a Python shell with

        import mtools
        mtools.__version__


