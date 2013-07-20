# Contributing to mtools

Contributions to mtools are very welcome. Please check if the particular bug / issue has already been
reported on the [mtools issues](https://github.com/rueckstiess/mtools/issues?state=open) page and create
a new issue if it doesn't exist yet.

### Development Installation

You can install mtools in "development" mode, which will not move it into the Python `site-packages` 
directory but keeps it in your local development directory instead. It will still install the necessary 
hooks so you will be able to use it like normal, both from Python and the command line. In addition,
you can modify the files directly in your local directory and test the changes right away.


Clone the repository
	
	cd /your/code/path
    git clone https://github.com/rueckstiess/mtools

Then change into the directory and install in "development" mode

	cd mtools
	sudo python setup.py develop


No changes to your `$PATH` and `$PYTHONPATH` environment variables are needed.



### Branching Model

mtools uses a simplified version of [this git branching model](http://nvie.com/posts/a-successful-git-branching-model/) 
by [@nvie](https://twitter.com/nvie).

The [master branch](https://github.com/rueckstiess/mtools) should only ever contain versioned releases. **Do not send
pull requests against the master branch.**

Development happens on the [develop branch](https://github.com/rueckstiess/mtools/tree/develop). 

First, fork the [main repository](https://github.com/rueckstiess/mtools) into your own github account (&lt;username&gt;). 
Then clone a copy to your local machine:

    git clone https://github.com/<username>/mtools

Now you need to add the upstream repository to pull in the latest changes.

    git remote add upstream https://github.com/rueckstiess/mtools
    git fetch upstream

To get a local `develop` branch you need to check out and track your remote `develop` branch:

    git checkout -b develop origin/develop

If you want to work on a bug or feature implementation, first pull in the latest changes from upstream:

    git checkout develop
    git pull upstream develop

Then create a feature/bugfix branch that forks off the local `develop` branch:

    git checkout -b feature-37-fast develop

The naming is not that relevant, but it's good practice to start with `feature-` or `bugfix-` and include the issue number
in the branch name (if available).

Now make your changes to the code. Commit as often as you like. Please use meaningful, descriptive git commit messages and
avoid `asdf` or `changed stuff` descriptions.

When you're happy with your changes, push your feature branch to github: 

    git push origin feature-37-fast

and raise a pull request against the upstream `develop` branch. Once the code is merged into the `develop` branch, 
you can pull the change from upstream develop and then delete your local and github feature/bugfix branch.

    git checkout develop
    git pull upstream develop
    git push origin --delete feature-37-fast
    git branch -d feature-37-fast


### Version Numbers

The versioning standard in mtools is pretty straight-forward. It follows a major.minor.micro version system. We decided to start
mtools at version 1.0.0  (it was already pretty stable and useable at that stage). Bugfixes and minor feature additions are released
as part of micro releases in roughly a two-week cycle:  1.0.0 --> 1.0.1 --> 1.0.2 --> ...

Minor releases will include more significant changes, including interface changes.  

I'm not sure yet what a major release constitutes :-)

The development version has the suffix `dev` attached. For example `1.0.1dev` is the development version leading up to `1.0.1` release.

Minor and major releases might have release candidates leading up to the final release. Those are marked with the suffix `rcX` where `X` 
is a number starting at 0. For example, version `1.2rc2` is the 3rd release candidate for upcoming release version `1.2`.

Github milestones and git tags are named with a prefix `v`, for example `v1.0.1`.


### Testing

mtools uses the [nose testing framework](https://github.com/nose-devs/nose). You can install it with `sudo pip install nose` or 
you can just run the test suite, which will take care of all the testing dependencies:

    python setup.py test

If you want to run the tests manually, go into the `mtools/test/` directory and run `nosetests`. The full test suite may take a while, as
some of the tests have to set up and tear down replica sets and sharded clusters, especially for mlaunch testing. You can skip the slow tests
with this command:

    nosetests -a '!slow'

If you implement a new feature anywhere in mlaunch, please write a test function or test class for the feature. If you fix a bug,
please re-run the test suite after the code change and make sure the tests still pass. Please think carefully before changing
a code and its related test concurrently, so it still tests the expected behavior and not what you consider as "fixed behavior".


