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

      sudo pip3 uninstall mtools

#. `Fork the mtools repository <https://help.github.com/articles/fork-a-repo/>`__
   to your own GitHub account.

#. Clone your mtools fork to your development environment. This step creates
   an mtools directory in the current directory, so you may want to switch
   to an appropriate directory first (for example ``~/code/``):

   .. code-block:: bash

      cd ~/code
      git clone https://github.com/<username>/mtools.git

#. Change into the mtools directory and check out the desired branch. All
   development should be based off the ``develop`` branch:

   .. code-block:: bash

      cd mtools
      git checkout develop

#. Install the mtools scripts in development mode using either:

   *  ``pip3`` (recommended as a convenience for installing additional
      dependencies):

      .. code-block:: bash

         sudo pip3 install -e '/path/to/cloned/repo[all]'

   *  ``setup.py``

      .. code-block:: bash

         sudo python3 setup.py develop

#. Test the installation by confirming that the scripts tab-complete from any
   directory:

   .. code-block:: bash

      mlogf<tab>

   This should auto-complete to ``mlogfilter``. Also confirm the current
   version, which should end in ``-dev`` for the ``develop`` branch:

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

mtools uses a simplified version of the `git branching
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
   branch. The branch should named after the
   `GitHub issue number <https://github.com/rueckstiess/mtools/issues/>`__
   you are working on. If there isn't a GitHub issue yet, please
   `create one <https://github.com/rueckstiess/mtools/issues/new>`__.

   .. code-block:: bash

      git checkout -b issue-12345 develop

#. Make your changes to the code. Commit as often as you like. Please use
   meaningful, descriptive commit messages and avoid ``asdf`` or ``changed
   stuff`` descriptions.

#. Add or update tests to confirm your changes are working as expected. See
   :ref:`testing` for more information.

#. When you're happy with your changes, push your feature branch to GitHub:

   .. code-block:: bash

      git push origin issue-12345

#. `Raise a pull request <https://help.github.com/articles/creating-a-pull-request/>`__
   against the upstream ``develop`` branch using the GitHub interface.

#. After the code is merged into the ``develop`` branch, you can pull the
   change from the upstream ``develop`` branch and delete your local feature
   or bug fix branch:

   .. code-block:: bash

      git checkout develop
      git pull upstream develop
      git push origin --delete issue-12345
      git branch -d issue-12345
