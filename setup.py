#!/usr/bin/env python

import codecs
import re
import os

try:
  from setuptools import setup
except:
  from distutils.core import setup


def find_version(*file_paths):
    version_file = codecs.open(os.path.join(os.path.abspath(
        os.path.dirname(__file__)), *file_paths), 'r').read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='paramgmt',
    version=find_version('paramgmt', '__init__.py'),
    description='Parallel SSH machine management',
    author='Nic McDonald',
    author_email='nicci02@hotmail.com',
    license='Apache License Version 2.0',
    url='http://github.com/google/paramgmt',
    packages=['paramgmt'],
    scripts=['bin/rhosts', 'bin/lcmd', 'bin/rcmd',
             'bin/rpull', 'bin/rpush', 'bin/rscript'],
    install_requires=['termcolor >= 1.1.0'],
    )
