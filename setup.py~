from setuptools import setup
import os
import subprocess
import sys


classifiers = """
Topic :: Multimedia :: Sound/Audio
Programming Language :: Python :: 3
"""


def get_version():
    return subprocess.check_output([sys.executable, "lilyponddist/__init__.py", "--version"]).decode('utf8').strip()


setup(name='lilyponddist',
      version=get_version(),
      url='https://github.com/gesellkammer/lilyponddist',
      description='Distribute lilypond as a pypi package', 
      long_description=open('README.rst').read(),
      classifiers=[l.strip() for l in classifiers.splitlines() if l.strip()],
      packages=['lilyponddist'],
      install_requires=[
          "appdirs",
          "progressbar"
      ],
)


