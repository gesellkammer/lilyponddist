lilyponddist
============

This package wraps the binary distribution of lilypond, allowing to install and use lilypond from python

Notice that this package installs lilypond from the releases provided by the lilypond team. It does not
conflict with any user-installed lilypond version, since it places lilypond at an ad-hoc place, without
modifying the PATH or any other part of the environment. 

At the moment the platforms supported are linux x86_64, windows x86_64 and macos x86_64. For macos 
arm64 the only way to install a native version is via homebrew. 

At first run ``lilyponddist`` will download the corresponding distribution. Whenever lilypond releases
a new binary this package will be updated with the new URLs. After the package itself is updated
the lilypond version can be updated by calling the ``update`` function


Installation
------------

.. code:: bash

    pip install --update lilyponddist


Example
-------

.. code:: python

    import lilyponddist
    import subprocess

    subprocess.call([lilyponddist.lilypondbin(), '/path/to/score.ly', '--pdf', '-o', '/path/to/output'])


	# Update if possible
	lilyponddist.update()

	# It can be checked if an update is available
	lilyponddist.needs_update()  # will return True if there is an update available

	# The current version can be checked via ``lilypond_version``. This returns the version of the
	# lilypond distribution installed via ``lilyponddist``. There is never an attempt to interact with
	# a user installed lilypond
	lilyponddist.lilypond_version()


