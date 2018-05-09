"""make-system-user

A utility to generate system-user assertions for Ubuntu Core devices.
"""

# NOTE: modified from https://github.com/pypa/sampleproject/blob/master/setup.py

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    readmeDescription = f.read()

setup(
    name='make-system-user',
    version='6',
    description='make-system-user creates system user assertion files for Ubuntu Core',
    long_description=readmeDescription,
    url='https://github.com/knitzsche/make-system-user',
    packages=["make_system_user"],
    install_requires=['snapcraft'],
    entry_points={
        'console_scripts': [
            'make_system_user = make_system_user.__main__:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/knitzsche/make-system-user/issues',
        'Source': 'https://github.com/knitzsche/make-system-user',
    },
)