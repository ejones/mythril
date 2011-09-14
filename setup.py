#!/usr/bin/env python
from setuptools import setup

setup(
    name='mythril',
    version='0.0.1',
    author='Evan Jones and Adam Gravitis',
    author_email='evan.q.jones@gmail.com',
    packages=[ 'mythril' ],
    url='http://github.com/ejones/mythril/',
    license='MIT',
    description='Lightweight library for transforming data and content',
    long_description=open( 'README.rst' ).read(),
    requires=[ 'simplejson' ],
    install_requires=[ 'simplejson >= 2.1.0' ])
