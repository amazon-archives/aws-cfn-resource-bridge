#!/usr/bin/env python

#==============================================================================
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#==============================================================================

import sys

from distutils.core import setup, Distribution
from aws.cfn import bridge

name = 'aws-cfn-resource-bridge'

if sys.version_info[0] == 2 and sys.version_info[1] < 6:
        print >> sys.stderr, "Python 2.6+ is required"
        sys.exit(1)

rpm_requires = ['python >= 2.6', 'python-daemon', 'python-botocore >= 0.17.0']
dependencies = ['python-daemon>=1.5.2', 'botocore>=0.17.0']

if sys.version_info[:2] == (2, 6):
    # For python2.6 we have to require argparse
    rpm_requires.append('python-argparse >= 1.1')
    dependencies.append('argparse>=1.1')

_opts = {
    'build_scripts': {'executable': '/usr/bin/env python'},
    'bdist_rpm': {'requires': rpm_requires}
}
_data_files = [('share/doc/%s-%s' % (name, bridge.__version__), ['NOTICE.txt', 'LICENSE']),
               ('init/redhat', ['init/redhat/cfn-resource-bridge']),
               ('init/ubuntu', ['init/ubuntu/cfn-resource-bridge'])]

try:
    import py2exe

    _opts['py2exe'] = {
        # TODO: Need to update this for this package
        'typelibs': [('{000C1092-0000-0000-C000-000000000046}', 1033, 1, 0),
                     ('{E34CB9F1-C7F7-424C-BE29-027DCC09363A}', 0, 1, 0)],
        'excludes': ['certifi', 'pyreadline', 'difflib', 'distutils', 'doctest', 'pdb', 'inspect', 'unittest',
                     'adodbapi'],
        'includes': ['chardet', 'dbhash', 'dumbdbm'],
        'dll_excludes': ['msvcr71.dll', 'w9xpopen.exe', ''],
        'compressed': True,
        'com_server': [],
        'ctypes_com_server': [],
        'service': ["aws.cfn.bridge.winbridge"],
        'isapi': [],
        'windows': [],
        'zipfile': 'library.zip',
        'console': ['bin/cfn-resource-bridge']
    }
    _data_files = [('', ['license/win/NOTICE.txt', 'license/win/LICENSE.rtf'])]
except ImportError:
    pass

setup_options = dict(
    name=name,
    version=bridge.__version__,
    description='A custom resource framework for AWS CloudFormation',
    long_description=open('README.md').read(),
    author='AWS CloudFormation',
    url='http://aws.amazon.com/cloudformation/',
    license='Apache License 2.0',
    scripts=['bin/cfn-resource-bridge'],
    classifiers=[],
    packages=[
        'aws',
        'aws.cfn',
        'aws.cfn.bridge'
    ],
    install_requires=dependencies,
    data_files=_data_files,
    options=_opts
)

setup(**setup_options)
