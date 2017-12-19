.. _development:

===========
Development
===========

You can install mtools in development mode, which does not move it into the
Python ``site-packages`` directory but keeps it in your local development
directory instead. It still installs the necessary hooks so you can use it like
normal, both from Python and the command line. In addition, you can modify the
files directly in your local directory and test the changes right away.

Using a development branch
~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Remove any existing mtools installation:

   .. code-block:: bash

      sudo pip uninstall mtools

#. Clone the current mtools GitHub repository to your computer. This step
   creates an ``mtools`` directory in the current directory, so you may want to
   switch to an appropriate directory first (for example ``~/code/``):

   .. code-block:: bash

      git clone https://github.com/rueckstiess/mtools.git

   If you have forked mtools to your own account, replace ``rueckstiess``
   with your own GitHub username.

#. Change into the ``mtools`` directory and check out the desired branch. This
   examples uses ``develop``:

   .. code-block:: bash

      cd mtools
      git checkout develop

#. Install the mtools scripts in development mode using either:

   *  ``pip`` (recommended as a convenience for installing additional
      dependencies):

      .. code-block:: bash

         sudo pip install -e '/path/to/cloned/repo[all]'

   * ``setup.py``

      .. code-block:: bash

         sudo python setup.py develop

#. Test the installation by confirming that the scripts tab-complete from any
   directory:

   .. code-block:: bash

      mlogf<tab>

   This should auto-complete to ``mlogfilter``. Also confirm the current
   version:

   .. code-block:: bash

      mlogfilter --version


Using the stable branch
~~~~~~~~~~~~~~~~~~~~~~~

#. To use the latest stable release of mtools, check out the master branch:

   .. code-block:: bash

      git checkout master

#. Confirm your current version with the ``--version`` parameter:

   .. code-block:: bash

      mloginfo --version


Making pull requests
~~~~~~~~~~~~~~~~~~~~

mtools uses a simplified version of `this git branching
model <http://nvie.com/posts/a-successful-git-branching-model/>`__ by
`@nvie <https://twitter.com/nvie>`__.

.. important::

   The `master branch <https://github.com/rueckstiess/mtools>`__ should only
   ever contain versioned releases. **Do not send pull requests against the
   master branch.**

Development happens on the `develop branch
<https://github.com/rueckstiess/mtools/tree/develop>`__.

#. Fork the `main repository <https://github.com/rueckstiess/mtools>`__
   into your own GitHub account.

#. Clone a copy to your local machine:

   .. code-block:: bash

      git clone https://github.com/<username>/mtools

#. Add the upstream repository to pull in the latest changes:

   .. code-block:: bash

      cd mtools
      git remote add upstream https://github.com/rueckstiess/mtools
      git fetch upstream

#. Check out and track your remote ``develop`` branch with a local branch:

   .. code-block:: bash

      git checkout -b develop origin/develop

#. If you want to work on a bug or feature implementation, pull in the
   latest changes from upstream:

   .. code-block:: bash

      git checkout develop
      git pull upstream develop

#. Create a feature or bug fix branch that forks off the local ``develop``
   branch:

   .. code-block:: bash

      git checkout -b feature-37-fast develop

   The naming is not that relevant, but it's good practice to start with
   ``feature-`` or ``bug-`` and include the issue number in the branch name
   (if available).

#. Make your changes to the code. Commit as often as you like. Please use
   meaningful, descriptive git commit messages and avoid ``asdf`` or ``changed
   stuff`` descriptions.

#. When you're happy with your changes, push your feature branch to GitHub:

   .. code-block:: bash

      git push origin feature-37-fast

#. Raise a pull request against the upstream ``develop`` branch using the
   GitHub interface. After the code is merged into the ``develop`` branch, you
   can pull the change from upstream develop and then delete your local and
   GitHub feature or bug fix branch:

   .. code-block:: bash

      git checkout develop
      git pull upstream develop
      git push origin --delete feature-37-fast
      git branch -d feature-37-fast
