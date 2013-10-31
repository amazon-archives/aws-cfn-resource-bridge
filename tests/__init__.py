#=======================================================================================================================
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the
# License. A copy of the License is located at
#
#     http://aws.amazon.com/asl/
#
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#=======================================================================================================================
import sys

# Use the backported version of unittest for python 2.6
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


def expect_error(error, message=None):
    """Simple decorator to make it easier to write tests that expect errors"""
    def decorator(func):
        def decorated_func(*args, **kwargs):
            # To support earlier versions of python, we have to use a try block.
            try:
                func(*args, **kwargs)
            except error, e:
                if message:
                    args[0].assertEqual(e.message, message)
            except Exception, e:
                args[0].fail(u"Should have failed with %s error and message '%s', but got %s instead" % (error, message, e))
            else:
                args[0].fail(u"Should have failed with %s error and message '%s'" % (error, message))
        return decorated_func
    return decorator