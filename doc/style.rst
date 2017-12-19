================
Style Guidelines
================

Before contributing code or documentation to the mtools project, please
familiarize yourself with these style guidelines.


Code guidelines
~~~~~~~~~~~~~~~

mtools is not overly prescriptive in terms of style: readability and
functionality are the main guiding principles. As a general rule, follow the
style used elsewhere in the code and always add meaningful comments.

If you implement a new feature anywhere in mlaunch, please write a test
function or test class for the feature and document it.

PEP 8
-----

mtools adheres to most of the standard Python guidelines provided in `PEP 8
<https://www.python.org/dev/peps/pep-0008/>`__, with the main exception being
that mixedCase function and variable names are permitted in order to match
usage in MongoDB (for example ``serverStatus``). `flake8
<http://flake8.pycqa.org/en/latest/>`__ is used for style checking.

Import order
------------

To improve readability, imports are sorted alphabetically by type of import.
`isort <https://readthedocs.org/projects/isort/>`__ is used for import
structure checking.

Docstrings (PEP 257)
--------------------

Please add a descriptive docstring to all new modules, classes, and functions.
`pydocstyle <http://www.pydocstyle.org>`__ is used to check docstrings comply
with `PEP 257 <https://www.python.org/dev/peps/pep-0257/>`__.


Documentation guidelines
~~~~~~~~~~~~~~~~~~~~~~~~

mtools documentation is written in `reStructuredText
<http://www.sphinx-doc.org/en/stable/rest.html>`__ and built using `Sphinx
<http://www.sphinx-doc.org/en/stable/index.html>`__.

The mtools documentation uses only standard RST and Sphinx syntax. As a general
rule, follow the style used in the rest of the documentation.

Indentation
-----------

Indent 3 spaces.

Line length
-----------

Limit all lines to 79 characters.

Exceptions:

-  code blocks
-  URLs

Code blocks
-----------

Use the ``code-block`` directive and specify the language. For example:

.. code-block:: text

   .. code-block:: python

      import re

