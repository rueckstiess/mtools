.. _testing:

=======
Testing
=======

mtools uses the following testing tools:

-  `tox <https://tox.readthedocs.io/en/latest/>`__ for creating a standardized
   test environment
-  `nose testing framework <https://github.com/nose-devs/nose>`__ for unit
   testing
-  `flake8 <http://flake8.pycqa.org/en/latest/>`__ for style checking
-  `isort <https://readthedocs.org/projects/isort/>`__ for import structure
   checking
-  `pydocstyle <http://www.pydocstyle.org>`__ for docstring (`PEP 257
   <https://www.python.org/dev/peps/pep-0257/>`__) checking
-  `doc8 <https://pypi.python.org/pypi/doc8>`__ for documentation style
   checking
-  `pyenchant <http://pythonhosted.org/pyenchant/>`__ for documentation spell
   checking

If you implement a new feature anywhere in mtools, please write a test
function or test class for the feature and document it. If you fix a bug,
please re-run the test suite after the code change and make sure the tests
still pass. Please think carefully before changing code and its related test
concurrently, so it still tests the expected behavior and not what you consider
as fixed behavior.


Prerequisites
~~~~~~~~~~~~~

tox is required for testing mtools and building the documentation:

.. code::

   $ sudo pip3 install tox


Using tox
~~~~~~~~~

tox creates a virtual environment and installs dependencies. To run the basic
code test suite:

.. code-block:: bash

   tox

To specify a particular test environment:

.. code-block:: bash

   tox -e flake8


Configuration
-------------

tox configuration is controlled by the `tox.ini
<https://github.com/rueckstiess/mtools/blob/develop/tox.ini>`__. It consists of
general tox settings, a series of testenvs that can be
invoked individually (e.g. ``tox -e doc``), and configuration for
certain tests.

.. code::

   [tox]
   minversion = 2.3
   envlist = py36
   skipsdist = True

   [testenv]
   deps =
       -r{toxinidir}/requirements.txt
       -r{toxinidir}/test-requirements.txt
   whitelist_externals = make
   commands = nosetests --detailed-errors --verbose --with-coverage --cover-package=mtools

   [testenv:doc]
   deps =
       -r{toxinidir}/requirements.txt
       doc8
       pyenchant
       sphinx
       sphinxcontrib-spelling
       sphinx_rtd_theme
   commands = doc8 doc
       make clean -C {toxinidir}/doc
       # make linkcheck -C {toxinidir}/doc -- currently cannot handle https
       make spelling -C {toxinidir}/doc
       make html -C {toxinidir}/doc

   [testenv:flake8]
   deps =
       pep8-naming
       flake8
   commands = flake8

   [testenv:isort]
   deps = isort
   commands =
       isort -c --diff -s .tox -o dateutil -o numpy -o pymongo -o bson -o nose

   [testenv:pydocstyle]
   deps = pydocstyle
   commands = pydocstyle --count

   [doc8]
   # Ignore target directories
   ignore-path = doc/_build*,.tox
   # File extensions to use
   extensions = .rst
   # Maximum line length should be 79
   max-line-length = 79

   [flake8]
   show-source = True
   # E123, E125 skipped as they are invalid PEP-8.
   # N802 skipped (function name should be lowercase)
   # N806 skipped (variable in function should be lowercase)
   # F401 skipped (imported but unused) after verifying current usage is valid
   # W503 skipped line break before binary operator
   # C901 skipped: 'MLaunchTool.init' is too complex
   ignore = E123,E125,N802,N806,F401,W503,C901
   builtins = _
   exclude=.venv,.git,.tox,dist,*lib/python*,*egg,*figures/*,__init__.py,build/*,setup.py,mtools/util/*,mtools/test/test_*
   count = true
   statistics = true
   max-complexity = 49


tox.ini options
---------------

[tox]
   -  **minversion**: minimum version of tox to use
   -  **envlist**: Python versions to test against. Also the list of testenvs
      ``tox`` runs when invoked without ``-e``.
   -  **skipdist**: run tox without requiring a ``setup.py`` file

[testenv]
   -  **deps**: packages required by ``[testenv]``.
   -  **whitelist_exernals**: commands sourced from the local operating system
      instead of being downloaded and installed by tox

[testenv:NAME]
   -  **doc**: Test and build the documentation
   -  **flake8**: run flake8 tests
   -  **isort**: run isort tests
   -  **pydocstyle**: run pydocstyle tests

[doc8]
   -  configuration options for the doc8 tests run in the ``doc`` environment

[flake8]
   -  configuration options for the flake8 tests run in the ``flake8``
      environment


Troubleshooting
---------------

In order to run more quickly, tox reuses elements of its virtual test
environment. However, when a configuration option changes or a new package is
available, tox does not automatically refresh its environment.

If you or someone else changes a configuration option in ``tox.ini`` or alters
a requirements file, you must force tox to recreate the test
environment. You can do this in two ways:

-  Add the ``-r, --recreate`` option the next time you run tox:

   .. code::

      $ tox -r

-  Delete the hidden ``.tox`` directory in the repository root where the
   environment is stored:

   .. code::

      $ rm -rf .tox

Most of the time, recreating the tox environment solves tox-related problems.
If you are still having issues, check the configuration in ``tox.ini``
is correct.

On rare occasions, a new version of an upstream dependency causes a failure.
The tox error output should provide some clue in the traceback. Package
maintainers will usually fix it these sorts of errors fairly quickly. In the
meantime, you can pin that package to the most recent working version in
the relevant requirements file. For example:

.. code::

   sphinx<=1.4.1
   sphinx_rtd_theme==0.1.9

If you do this, please retest every few days and remove the version requirement
when the package is fixed.


Documentation builds
~~~~~~~~~~~~~~~~~~~~

mtools documentation is written in `reStructuredText
<http://www.sphinx-doc.org/en/stable/rest.html>`__ and built using `Sphinx
<http://www.sphinx-doc.org/en/stable/index.html>`__.

You can test and build the documentation by running:

.. code-block:: bash

   tox -e doc

View the built HTML by opening ``doc/_build/html/index.html``.

If the spelling checker flags a word that should be ignored, you can add it
to the ``doc/spelling_wordlist.txt`` file.
