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
from tests import unittest, expect_error

from aws.cfn.bridge.resources import CustomResource


class TestCustomResource(unittest.TestCase):
    def setUp(self):
        self.options = {
            'queue_url': 'https://queue.us-east-1.amazonaws.com',
            'default_action': 'action-default',
        }

    def test_expect_queue_to_be_set(self):
        resource = CustomResource('name', 'file', self.options)
        self.assertEqual(resource.queue_url, 'https://queue.us-east-1.amazonaws.com')

    @expect_error(ValueError, "[name] in 'file' is missing 'queue_url' attribute")
    def test_expect_queue_to_be_required(self):
        del self.options['queue_url']
        CustomResource('name', 'file', self.options)

    def test_expect_name_to_be_set(self):
        resource = CustomResource('name', 'file', self.options)
        self.assertEqual(resource.name, 'name')

    def test_expect_source_file_to_be_set(self):
        resource = CustomResource('name', 'file', self.options)
        self.assertEqual(resource.source_file, 'file')

    def test_expect_region_to_be_parsed(self):
        resource = CustomResource('name', 'title', self.options)
        self.assertEqual(resource.region, 'us-east-1')

    def test_expect_region_to_be_parsed_from_sqs_url(self):
        self.options['queue_url'] = "https://sqs.us-west-1.amazonaws.com"
        resource = CustomResource('name', 'title', self.options)
        self.assertEqual(resource.region, 'us-west-1')

    def test_expect_region_option_to_override(self):
        self.options['region'] = 'fun-region'
        resource = CustomResource('name', 'title', self.options)
        self.assertEqual(resource.region, 'fun-region')

    def test_expect_region_option_to_set(self):
        self.options['queue_url'] = "http://noregion"
        self.options['region'] = 'my-region'
        resource = CustomResource('name', 'title', self.options)
        self.assertEqual(resource.region, 'my-region')

    @expect_error(ValueError, "[name] in 'title' must define 'region' attribute")
    def test_expect_region_to_be_required(self):
        self.options['queue_url'] = "http://noregion"
        CustomResource('name', 'title', self.options)

    def test_expect_default_action_to_be_used(self):
        resource = CustomResource('name', 'file', self.options)
        self.assertEqual(resource._create_action, 'action-default')
        self.assertEqual(resource._update_action, 'action-default')
        self.assertEqual(resource._delete_action, 'action-default')

    def test_expect_custom_action_to_override_default(self):
        self.options.update({
            'create_action': 'create',
            'delete_action': 'delete',
            'update_action': 'update'
        })
        resource = CustomResource('name', 'file', self.options)
        self.assertEquals(resource._create_action, 'create')
        self.assertEquals(resource._update_action, 'update')
        self.assertEquals(resource._delete_action, 'delete')

    @expect_error(ValueError, "[bad_create] in 'file' must define create_action")
    def test_expect_create_action_to_be_required(self):
        self.options.update({'create_action': ''})
        CustomResource('bad_create', 'file', self.options)

    @expect_error(ValueError, "[bad_delete] in 'file' must define delete_action")
    def test_expect_delete_action_to_be_required(self):
        self.options.update({'delete_action': ''})
        CustomResource('bad_delete', 'file', self.options)

    @expect_error(ValueError, "[bad_update] in 'file' must define update_action")
    def test_expect_update_action_to_be_required(self):
        self.options.update({'update_action': ''})
        CustomResource('bad_update', 'file', self.options)

if __name__ == "__main__":
    unittest.main()
