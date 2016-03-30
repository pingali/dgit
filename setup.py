#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = []

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='dgit',
    version='0.1.0',
    description="Git for datasets with support for multiple backends",
    long_description=readme + '\n\n' + history,
    author="Venkata Pingali",
    author_email='pingali@gmail.com',
    url='https://github.com/pingali/dgit',
    packages=[
        'dgit',
    ],
    scripts=[
        'bin/dgit'
    ],
    package_dir={'dgit': 'dgitcore'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='dgit',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
)
