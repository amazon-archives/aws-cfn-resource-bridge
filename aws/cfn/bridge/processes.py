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
import subprocess
import os


class ProcessResult(object):
    """
    Return object for ProcessHelper

    """
    def __init__(self, returncode, stdout, stderr):
        self._returncode = returncode
        self._stdout = stdout if not stdout else stdout.decode('utf-8')
        self._stderr = stderr if not stderr else stderr.decode('utf-8')

    @property
    def returncode(self):
        return self._returncode

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr


class ProcessHelper(object):
    """
    Helper to simplify command line execution

    """
    def __init__(self, cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=None, cwd=None):
        self._cmd = cmd
        self._stdout = stdout
        self._stderr = stderr
        if not env:
            self._env = None
        elif os.name == 'nt':  # stringify the environment in Windows, which cannot handle unicodes
            # Windows requires inheriting some of the parent process' environment, so just take them all.
            self._env = dict(((str(k), str(v)) for k, v in os.environ.iteritems()))
            self._env.update(dict(((str(k), str(v)) for k, v in env.iteritems())))
        else:
            self._env = dict(os.environ.copy())
            self._env.update(dict(env))

        self._cwd = cwd

    def call(self):
        """
        Calls the command, returning a tuple of (returncode, stdout, stderr)
        """

        process = subprocess.Popen(self._cmd, stdout=self._stdout, stderr=self._stderr,
                                   shell=isinstance(self._cmd, basestring), env=self._env, cwd=self._cwd)
        return_data = process.communicate()

        return ProcessResult(process.returncode, return_data[0], return_data[1])