#!/usr/bin/env python
# -*- coding: utf-8 -*-

# rafi.mx build script
# ===

import subprocess
import re

rev_list = subprocess.check_output(['git', 'rev-list', '--all'])
commit_count = rev_list.decode('utf-8').count('\n')

with open('setup.py') as f:
    setup = f.read()

setup = re.sub(
    "MICRO_VERSION = '[0-9]+'",
    "MICRO_VERSION = '{}'".format(commit_count), setup)

major = re.search('MAJOR_VERSION = \'([0-9]+)\'', setup).groups()[0]
minor = re.search('MINOR_VERSION = \'([0-9]+)\'', setup).groups()[0]
micro = re.search('MICRO_VERSION = \'([0-9]+)\'', setup).groups()[0]
version = '{}.{}.{}'.format(major, minor, micro)

with open('setup.py', 'w') as f:
    f.write(setup)

with open('src/mx/__init__.py') as f:
    init = f.read()

with open('src/mx/__init__.py', 'w') as f:
    f.write(
        re.sub('__version__ = \'[0-9.]+\'',
               '__version__ = \'{}\''.format(version), init))
