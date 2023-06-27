lilyponddist
============

This package wraps the binary distribution of lilypond, allowing to install it in order to be used from python.

At the moment it is hardcoded to download and install lilypond 2.24.1. The platforms supported are 
linux x86_64 and windows x86_64. For macos it is recommended to install via homebrew, which supports 
both x64 and arm64.

At first run it will download the corresponding distribution.

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


TODO
----

* Reimplement this using pooch
