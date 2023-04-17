from setuptools import setup
import os


classifiers = """
Topic :: Multimedia :: Sound/Audio
Programming Language :: Python :: 3
"""

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


datafiles = package_files('lilyponddist/data')
print("datafiles", datafiles)

setup(name='lilyponddist',
      version='0.1.0',
      url='https://github.com/gesellkammer/lilyponddist',
      description='Distribute lilypond as a pypi package', 
      long_description=open('README.rst').read(),
      classifiers=[l.strip() for l in classifiers.splitlines() if l.strip()],
      packages=['lilyponddist'],
      install_requires=[
      ],
      include_package_data=True,
      package_data={'': datafiles}
)


