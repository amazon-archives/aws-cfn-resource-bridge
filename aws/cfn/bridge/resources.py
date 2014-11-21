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
import re
from .processes import ProcessHelper
from . import util
from .vendored.botocore import session as bc_session

try:
    import simplejson as json
except ImportError:
    import json

import logging
from .vendored.botocore.vendored import requests
import uuid

log = logging.getLogger("cfn.resourcebridge")

_OPTION_QUEUE_URL = 'queue_url'
_OPTION_DEFAULT_ACTION = 'default_action'
_OPTION_CREATE_ACTION = 'create_action'
_OPTION_DELETE_ACTION = 'delete_action'
_OPTION_UPDATE_ACTION = 'update_action'

_OPTION_CREATE_TIMEOUT = 'create_timeout'
_OPTION_DELETE_TIMEOUT = 'delete_timeout'
_OPTION_UPDATE_TIMEOUT = 'update_timeout'
_OPTION_TIMEOUT = 'timeout'

_OPTION_FLATTEN = 'flatten'
_OPTION_SERVICE_TOKEN = 'service_token'
_OPTION_RESOURCE_TYPE = 'resource_type'

_OPTION_REGION = 'region'

# Our default timeout, set to 30 minutes
_DEFAULT_TIMEOUT = 30 * 60


class CustomResource(object):
    def __init__(self, name, source_file, options):
        # The source configuration file this resource was defined in, useful for error messages and debugging
        self._source_file = source_file
        self._name = name

        # Ensure a queue url has been defined
        self._queue_url = options.get(_OPTION_QUEUE_URL, None)
        if not self._queue_url:
            raise ValueError(u"[%s] in '%s' is missing 'queue_url' attribute" % (name, source_file))

        self._region = None

        # Try to parse the region from the queues/sqs prefixed urls.
        region_match = re.match(r"https?://(?:queue|sqs)\.([^.]+?)\.amazonaws\..+", self._queue_url, re.I | re.U)
        if region_match:
            self._region = region_match.group(1)

        self._region = options.get(_OPTION_REGION, self._region)
        if not self._region:
            raise ValueError(u"[%s] in '%s' must define 'region' attribute" % (name, source_file))

        # Determine if we should flatten the resource properties in environment variables. (Default to true)
        self._flatten = options.get(_OPTION_FLATTEN, 'true').lower() not in ['0', 'no', 'false', 'off']

        # Store the required service token, if it has any
        self._service_token = options.get(_OPTION_SERVICE_TOKEN, None)

        # Store the resource type supported, if defined
        self._resource_type = options.get(_OPTION_RESOURCE_TYPE, None)

        # Determine the default timeout
        timeout = options.get(_OPTION_TIMEOUT, _DEFAULT_TIMEOUT)

        # Set our timeout for actions from the queue
        self._create_timeout = int(options.get(_OPTION_CREATE_TIMEOUT, timeout))
        self._delete_timeout = int(options.get(_OPTION_DELETE_TIMEOUT, timeout))
        self._update_timeout = int(options.get(_OPTION_UPDATE_TIMEOUT, timeout))

        # Determine our default action
        action = options.get(_OPTION_DEFAULT_ACTION, None)

        # Set our actions for each type of event
        self._create_action = options.get(_OPTION_CREATE_ACTION, action)
        if not self._create_action:
            raise ValueError(u"[%s] in '%s' must define %s" % (name, source_file, _OPTION_CREATE_ACTION))

        self._delete_action = options.get(_OPTION_DELETE_ACTION, action)
        if not self._delete_action:
            raise ValueError(u"[%s] in '%s' must define %s" % (name, source_file, _OPTION_DELETE_ACTION))

        self._update_action = options.get(_OPTION_UPDATE_ACTION, action)
        if not self._update_action:
            raise ValueError(u"[%s] in '%s' must define %s" % (name, source_file, _OPTION_UPDATE_ACTION))

    @property
    def name(self):
        return self._name

    @property
    def queue_url(self):
        return self._queue_url

    @property
    def source_file(self):
        return self._source_file

    @property
    def resource_type(self):
        return self._resource_type

    @property
    def service_token(self):
        return self._service_token

    @property
    def region(self):
        return self._region

    def determine_event_timeout(self, event):
        if event.request_type == "Create":
            timeout = self._create_timeout
        elif event.request_type == "Delete":
            timeout = self._delete_timeout
        else:
            timeout = self._update_timeout

        return timeout

    def process_event(self, event):
        # TODO: Probably need to pull this out...
        if event.request_type == "Create":
            command = self._create_action
        elif event.request_type == "Delete":
            command = self._delete_action
        else:
            command = self._update_action

        # Run our command
        command_result = ProcessHelper(command, env=event.create_environment(self._flatten)).call()

        result_text = command_result.stdout.strip()
        success = True
        if result_text:
            try:
                result_attributes = json.loads(result_text)
                if not isinstance(result_attributes, dict):
                    raise ValueError(u"Results must be a JSON object")
            except:
                log.error(u"Command %s-%s (%s) returned invalid data: %s", self._name, event.request_type,
                          command, result_text)
                success = False
                result_attributes = {}
        else:
            result_attributes = {}

        if command_result.returncode:
            log.error(u"Command %s-%s (%s) failed", self._name, event.request_type, command)
            log.debug(u"Command %s output: %s", self._name, result_text)
            log.debug(u"Command %s stderr: %s", self._name, command_result.stderr.strip())
            success = False
        else:
            log.info(u"Command %s-%s succeeded", self._name, event.request_type)
            log.debug(u"Command %s output: %s", self._name, result_text)
            log.debug(u"Command %s stderr: %s", self._name, command_result.stderr.strip())

        event.send_result(success, result_attributes)


class Message(object):
    def __init__(self, queue_url, region, message):
        self._queue_url = queue_url
        self._message = message
        self._region = region

    def parse_message(self):
        return json.loads(json.loads(self._message["Body"])["Message"])

    def delete(self):
        sqs = bc_session.get_session().get_service("sqs")
        delete = sqs.get_operation("DeleteMessage")
        http_response, response_data = delete.call(sqs.get_endpoint(self._region),
                                                   queue_url=self._queue_url,
                                                   receipt_handle=self._message.get("ReceiptHandle"))

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200:
            log.error(u"Failed to delete message from queue %s with status_code %s: %s" %
                      (self._queue_url, http_response.status_code, response_data))

    def change_message_visibility(self, timeout):
        sqs = bc_session.get_session().get_service("sqs")
        delete = sqs.get_operation("ChangeMessageVisibility")
        http_response, response_data = delete.call(sqs.get_endpoint(self._region),
                                                   queue_url=self._queue_url,
                                                   receipt_handle=self._message.get("ReceiptHandle"),
                                                   visibility_timeout=timeout)

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200:
            log.error(u"Failed to change visibility of message from queue %s with status_code %s: %s" %
                      (self._queue_url, http_response.status_code, response_data))


class ResourceEvent():
    def __init__(self, message):
        self._message = message
        self._event = self._message.parse_message()

        # Ensure the event has some required fields.
        if not "StackId" in self._event:
            raise ValueError(u"ResourceEvent requires StackId")

        if not "ResponseURL" in self._event:
            raise ValueError(u"ResourceEvent requires ResponseURL")

        if not "RequestType" in self._event:
            raise ValueError(u"ResourceEvent requires RequestType")

        if not "ResourceType" in self._event:
            raise ValueError(u"ResourceEvent requires ResourceType")

        request_type = self._event["RequestType"]
        valid_types = ["Create", "Delete", "Update"]
        if not request_type or request_type not in valid_types:
            raise ValueError(u"ResourceEvent requires RequestType to be %s", valid_types)

        if not "LogicalResourceId" in self._event:
            raise ValueError(u"ResourceEvent requires LogicalResourceId")

        if not "RequestId" in self._event:
            raise ValueError(u"ResourceEvent requires RequestId")

    @property
    def request_type(self):
        return self._event["RequestType"]

    @property
    def resource_type(self):
        return self._event["ResourceType"]

    @staticmethod
    def _dict_to_env(dict_in, prefix, env):
        for key in dict_in:
            value = dict_in[key]
            new_key = prefix + key
            if isinstance(value, dict):
                env = ResourceEvent._dict_to_env(value, new_key + "_", env)
            else:
                env[new_key] = str(value)

        return env

    def create_environment(self, flatten=True):
        if flatten:
            return ResourceEvent._dict_to_env(self._event, "Event_", {})
        else:
            return {"EventProperties": json.dumps(self._event, skipkeys=True)}

    def get(self, prop):
        """Attempts to retrieve the provided resource property; returns None if not found"""
        return self._event.get('ResourceProperties', {}).get(prop)

    def increase_timeout(self, timeout):
        """Attempts to increase the message visibility timeout."""
        self._message.change_message_visibility(timeout)

    def delete(self):
        self._message.delete()

    def send_result(self, success, attributes):
        attributes = attributes if attributes else {}
        # Build up our required attributes
        source_attributes = {
            "Status": "SUCCESS" if success else "FAILED",
            "StackId": self._event["StackId"],
            "RequestId": self._event["RequestId"],
            "LogicalResourceId": self._event["LogicalResourceId"]
        }

        source_attributes['PhysicalResourceId'] = self._event.get('PhysicalResourceId')
        if not source_attributes['PhysicalResourceId']:
            source_attributes['PhysicalResourceId'] = str(uuid.uuid4())

        if not success:
            source_attributes["Reason"] = "Unknown Failure"

        source_attributes.update(attributes)
        log.debug(u"Sending result: %s", source_attributes)
        self._put_response(source_attributes)

    @util.retry_on_failure(max_tries=10)
    def __send(self, data):
        requests.put(self._event["ResponseURL"],
                     data=json.dumps(data),
                     headers={"Content-Type": ""},
                     verify=True).raise_for_status()

    def _put_response(self, data):
        try:
            self.__send(data)
            log.info(u"CloudFormation successfully sent response %s", data["Status"])
        except IOError, e:
            log.exception(u"Failed sending CloudFormation response")

    def __repr__(self):
        return str(self._event)
