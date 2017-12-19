========
Releases
========

The versioning standard in mtools is pretty straight-forward. It follows a
major.minor.micro version system. We decided to start mtools at version 1.0.0
as it was already pretty stable and usable at that stage.

Bug fixes and minor feature additions are released periodically as part of
micro releases. Minor releases will include more significant changes, including
interface changes. We're not sure yet what a major release constitutes :-).

The development version has the suffix ``dev`` attached. For example
``1.0.1-dev`` is the development version leading up to a ``1.0.1`` release.

Minor and major releases might have release candidates leading up to the final
release. Those are marked with the suffix ``rcX`` where ``X``
is a number starting at 0. For example, version ``1.2.0-rc2`` is the 3rd
release candidate for upcoming release version ``1.2.0``.

GitHub milestones and git tags are named with a prefix ``v``, for example
``v1.0.1``.


Releasing a new version
~~~~~~~~~~~~~~~~~~~~~~~

#. Create a release branch, named ``release-x.y.z`` where ``x.y.z`` is the
   version to be released.
#. Increase the version in ``./mtools/version.py`` from ``x.y.z-dev`` to
   ``x.y.z``.
#. Run tests via ``nosetests`` and make sure they pass
#. Update README.md and CHANGES.md accordingly
#. Any other cleanup tasks
#. (optional) leave the release branch for a few days to give others a chance
   to test it before releasing
#. Run ``twine upload dist/*`` to publish the new version to pip (if you have
   permissions, otherwise ask someone who does, e.g. @rueckstiess or @stennie).
#. Merge the release branch into ``master``
#. Merge the release branch into ``develop``
#. Delete the ``release-x.y.z`` branch
#. Bump the version on the develop branch (in ``./mtools/version.py``) to
   ``x.y.(z+1)-dev``.
