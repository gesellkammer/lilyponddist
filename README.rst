lilyponddist
============

This package wraps the binary distribution of lilypond, allowing to install and use lilypond from python

Notice that this package installs lilypond from the releases provided by the lilypond team. It does not
conflict with any user-installed lilypond version, since it places lilypond at an ad-hoc place, without
modifying the PATH or any other part of the environment. 

At the moment these platforms are supported: linux-x86_64, windows-x86_64, darwin-x86_64 and darwin-arm64.
Support for macos (darwin) arm64 is only with an unstable version (2.25), but tests show that
this version works correctly with macos >= 13

The first time it is asked for the path of the lilypond binary, **lilyponddist** will download
the given version (or the latest version if no version is specified) and the user can call that
binary as if it was any regular installation of lilypond. Any subsequent call will use the already installed
version. 

**lilyponddist** follows the release process of lilypond closely and any new binary release is incorporated
to the registry of downloads. Updating lilyponddist through pip will make these updates available via 
the ``update`` function.  


Installation
------------

.. code:: bash

    pip install lilyponddist


Example
-------

.. code:: python

    import lilyponddist
    import subprocess

    subprocess.call([lilyponddist.lilypondbin(), '/path/to/score.ly', '--pdf', '-o', '/path/to/output'])


Documentation
-------------

### ``lilypondbin(version='')``



### ``update()``

Update the current lilypond installation if possible


### ``can_update()``

Checks if an update is available. This functions
will return the latest version to update to, or None if
there are no updates available 



	# The current version can be checked via ``lilypond_version``. This returns the version of the
	# lilypond distribution installed via ``lilyponddist``. There is never an attempt to interact with
	# a user installed lilypond
	lilyponddist.lilypond_version()

	# All available versions can be queried via
	lilyponddist.avaialable_versions()

	# Installed versions can be queried via
	lilyponddist.installed_versions()

	


