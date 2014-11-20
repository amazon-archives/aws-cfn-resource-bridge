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
__author__ = 'aws'
__version__ = '0.2'

import logging.config
import os.path
import sys
import StringIO

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

_config = """[loggers]
keys=root,cfnresourcebridge
[handlers]
keys=%(all_handlers)s
[formatters]
keys=amzn
[logger_root]
level=NOTSET
handlers=%(root_handler)s
[logger_cfnresourcebridge]
level=NOTSET
handlers=%(root_handler)s
qualname=cfn.resourcebridge
propagate=0
[logger_wire]
level=NOTSET
handlers=%(wire_handler)s
qualname=wire
propagate=0
[handler_default]
class=handlers.RotatingFileHandler
level=%(conf_level)s
formatter=amzn
args=('%(conf_file)s', 'a', 5242880, 5, 'UTF-8')
[handler_wire]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=amzn
args=('%(wire_file)s', 'a', 5242880, 5, 'UTF-8')
[handler_tostderr]
class=StreamHandler
level=%(conf_level)s
formatter=amzn
args=(sys.stderr,)
[formatter_amzn]
format=%(asctime)s [%(levelname)s] %(message)s
datefmt=
class=logging.Formatter
"""


def _get_log_file(filename):
    if os.name == 'nt':
        logdir = os.path.expandvars(r'${SystemDrive}\cfn\log')
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        return logdir + os.path.sep + filename

    return '/var/log/%s' % filename


def configure_logging(level='INFO', quiet=False, filename='cfn-resource-bridge.log', log_dir=None, wire_log=True):
    if not log_dir:
        output_file = _get_log_file(filename)
        wire_file = _get_log_file('cfn-resource-bridge-wire.log') if wire_log else None
    else:
        output_file = os.path.join(log_dir, filename)
        wire_file = os.path.join(log_dir, 'cfn-resource-bridge-wire.log') if wire_log else None

    config = {'conf_level': level,
              'all_handlers': 'default' + (',wire' if wire_log else ''),
              'root_handler': 'default',
              'wire_handler': 'wire' if wire_log else None,
              'conf_file': output_file}

    if wire_file:
        config['wire_file'] = wire_file

    try:
        logging.config.fileConfig(StringIO.StringIO(_config), config)
        if not wire_log:
            logging.getLogger('wire').addHandler(NullHandler())
    except IOError:
        config['all_handlers'] = 'tostderr'
        config['root_handler'] = 'tostderr'
        config['wire_handler'] = None
        if not quiet:
            print >> sys.stderr, "Could not open %s for logging.  Using stderr instead." % output_file
        logging.config.fileConfig(StringIO.StringIO(_config), config)
        logging.getLogger('wire').addHandler(NullHandler())

configure_logging(quiet=True, wire_log=True)
