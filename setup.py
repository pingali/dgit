#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

readme = """dgit is an application on top of git.

A lot of data-scientists' time goes towards generating, shaping, and
using datasets. dgit enables organizing and using datasets with
minimal effort.

dgit uses git for version management but structures the repository
content, and interface to suit data management tasks.

Read `documentation <https://dgit.readthedocs.org>`_

Note: Only Python 3 supported for now

"""

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'boto3',
    'click',
    'PyYAML',
    'glob2',
    'messytables',
    'parse',
    'daff',
    'sh',
    'numpydoc'
]

dependency_links = [
]

setup(
    name='dgit',
    version='0.1.6',
    description="Git wrapper for Managing Datasets",
    long_description=readme + '\n\n' + history,
    author="Venkata Pingali",
    author_email='pingali@gmail.com',
    url='https://github.com/pingali/dgit',
    packages=[
        'dgitcore',
    ],
    scripts=[
        'bin/dgit'
    ],
    package_dir={'dgitcore': 'dgitcore'},
    include_package_data=True,
    install_requires=requirements,
    dependency_links=dependency_links,
    license="MIT",
    zip_safe=False,
    keywords='git data datasets versioning cvs',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
)
