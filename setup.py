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

from distutils.core import setup
from aws.cfn import bridge

name = 'aws-cfn-resource-bridge'

if sys.version_info[0] == 2 and sys.version_info[1] < 6:
        print >> sys.stderr, "Python 2.6+ is required"
        sys.exit(1)

rpm_requires = ['python >= 2.6', 'python-daemon', 'python-six >= 1.1.0', 'python-jmespath >= 0.5.0',
                'python-dateutil >= 2.1']
dependencies = ['python-daemon>=1.5.2', 'six>=1.1.0', 'jmespath>=0.5.0', 'python-dateutil>=2.1']

if sys.version_info[:2] == (2, 6):
    # For python2.6 we have to require argparse
    rpm_requires.append('python-argparse >= 1.1')
    dependencies.append('argparse>=1.1')

    ### Required for botocore. ###
    rpm_requires.append('python-ordereddict >= 1.1')
    dependencies.append('ordereddict>=1.1')
    rpm_requires.append('python-simplejson >= 3.3.0')
    dependencies.append('simplejson>=3.3.0')
    ### End botocore dependencies ###

_opts = {
    'build_scripts': {'executable': '/usr/bin/env python'},
    'bdist_rpm': {'requires': rpm_requires}
}
_data_files = [('share/doc/%s-%s' % (name, bridge.__version__), ['NOTICE.txt', 'LICENSE']),
               ('init/redhat', ['init/redhat/cfn-resource-bridge']),
               ('init/ubuntu', ['init/ubuntu/cfn-resource-bridge'])]
_package_data = {
    'aws.cfn.bridge.vendored.botocore': ['data/*.json', 'data/aws/*.json', 'data/aws/*/*.json'],
    'aws.cfn.bridge.vendored.botocore.vendored.requests': ['*.pem']
}

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
    _data_files = [('', ['license/win/NOTICE.txt', 'license/win/LICENSE.rtf', 'aws/cfn/bridge/vendored/botocore/vendored/requests/cacert.pem'])]
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
        'aws.cfn.bridge',
        'aws.cfn.bridge.vendored',
        'aws.cfn.bridge.vendored.botocore',
        'aws.cfn.bridge.vendored.botocore.vendored',
        'aws.cfn.bridge.vendored.botocore.vendored.requests',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages.charade',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages.urllib3',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages.urllib3.contrib',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages.urllib3.packages',
        'aws.cfn.bridge.vendored.botocore.vendored.requests.packages.urllib3.packages.ssl_match_hostname',
    ],
    install_requires=dependencies,
    data_files=_data_files,
    package_data=_package_data,
    options=_opts
)

setup(**setup_options)
