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
from aws.cfn.bridge.processes import ProcessHelper
from aws.cfn.bridge import util
import botocore.session

try:
    import simplejson as json
except ImportError:
    import json

import logging
import requests
import uuid

log = logging.getLogger("cfn.resourcebridge")

_OPTION_QUEUE_URL = 'queue_url'
_OPTION_DEFAULT_ACTION = 'default_action'
_OPTION_CREATE_ACTION = 'create_action'
_OPTION_DELETE_ACTION = 'delete_action'
_OPTION_UPDATE_ACTION = 'update_action'

_OPTION_CREATE_TIMEOUT = 'create_timeout'
_OPTION_DELETE_TIMEOUT = 'create_timeout'
_OPTION_UPDATE_TIMEOUT = 'create_timeout'
_OPTION_TIMEOUT = 'timeout'

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
            # TODO: Should we simply warn and continue on?
            raise ValueError(u"[%s] in '%s' is missing 'queue_url' attribute" % (name, source_file))

        self._region = None

        # Try to parse the region from the queues/sqs prefixed urls.
        region_match = re.match(r"https?://(?:queue|sqs)\.([^.]+?)\.amazonaws\..+", self._queue_url, re.I | re.U)
        if region_match:
            self._region = region_match.group(1)

        self._region = options.get(_OPTION_REGION, self._region)
        if not self._region:
            raise ValueError(u"[%s] in '%s' must define 'region' attribute" % (name, source_file))

        # Determine the default timeout
        timeout = options.get(_OPTION_TIMEOUT, _DEFAULT_TIMEOUT)

        # Set our timeout for actions from the queue
        self._create_timeout = int(options.get(_OPTION_CREATE_TIMEOUT, timeout))
        self._delete_timeout = int(options.get(_OPTION_DELETE_TIMEOUT, timeout))
        self._update_timeout = int(options.get(_OPTION_UPDATE_TIMEOUT, timeout))

        # Determine our default action
        action = options.get(_OPTION_DEFAULT_ACTION, None)

        # TODO: Must we define all scripts? Or can we have a default "success" response?
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
        command_result = ProcessHelper(command, env=event.create_environment()).call()

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
            success = False
        else:
            log.info(u"Command %s-%s succeeded", self._name, event.request_type)
            log.debug(u"Command %s output: %s", self._name, result_text)

        event.send_result(success, result_attributes)

    def retrieve_events(self, max_events=1):
        """Attempts to retrieve events for the custom resource"""
        session = botocore.session.get_session()
        sqs = session.get_service("sqs")
        receive = sqs.get_operation("ReceiveMessage")
        http_response, response_data = receive.call(sqs.get_endpoint(self.region),
                                                    queue_url=self.queue_url,
                                                    wait_time_seconds=20,
                                                    max_number_of_messages=max_events)

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200 or not "Messages" in response_data:
            log.error(u"[%s] Failed to retrieve messages from queue %s with status_code %s: %s" %
                      (self.name, self.queue_url, http_response.status_code, response_data))
            return []

        events = []
        for msg in response_data.get("Messages", []):
            # Construct a message that we can parse into events.
            message = Message(self._queue_url, self._region, msg)

            try:
                # Try to parse our message as a custom resource event
                event = ResourceEvent(message)

                events.append(event)
            except Exception:
                log.exception(u"Invalid message received; will delete from queue: %s", msg)
                message.delete()

        return events


class Message(object):
    def __init__(self, queue_url, region, message):
        self._queue_url = queue_url
        self._message = message
        self._region = region

    def parse_message(self):
        return json.loads(json.loads(self._message["Body"])["Message"])

    def delete(self):
        sqs = botocore.session.get_session().get_service("sqs")
        delete = sqs.get_operation("DeleteMessage")
        http_response, response_data = delete.call(sqs.get_endpoint(self._region),
                                                   queue_url=self._queue_url,
                                                   receipt_handle=self._message.get("ReceiptHandle"))

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200:
            log.error(u"Failed to delete message from queue %s with status_code %s: %s" %
                      (self._queue_url, http_response.status_code, response_data))

    def change_message_visibility(self, timeout):
        sqs = botocore.session.get_session().get_service("sqs")
        delete = sqs.get_operation("ChangeMessageVisibility")
        http_response, response_data = delete.call(sqs.get_endpoint(self._region),
                                                   queue_url=self._queue_url,
                                                   receipt_handle=self._message.get("ReceiptHandle"),
                                                   visibility_timeout=timeout)

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200:
            log.error(u"Failed to delete message from queue %s with status_code %s: %s" %
                      (self._queue_url, http_response.status_code, response_data))


class ResourceEvent():
    def __init__(self, message):
        self._message = message
        self._event = self._message.parse_message()

        # Ensure the event has some required fields.
        if not self._event["StackId"]:
            raise ValueError(u"ResourceEvent requires StackId")

        if not self._event["ResponseURL"]:
            raise ValueError(u"ResourceEvent requires ResponseURL")

        request_type = self._event["RequestType"]
        valid_types = ["Create", "Delete", "Update"]
        if not request_type or request_type not in valid_types:
            raise ValueError(u"ResourceEvent requires RequestType to be %s", valid_types)

        if not self._event["LogicalResourceId"]:
            raise ValueError(u"ResourceEvent requires LogicalResourceId")

        if not self._event["RequestId"]:
            raise ValueError(u"ResourceEvent requires RequestId")

    @property
    def request_type(self):
        return self._event["RequestType"]

    @staticmethod
    def _dict_to_env(dict_in, prefix, env):
        for key in dict_in:
            value = dict_in[key]
            new_key = prefix + key
            if isinstance(value, dict):
                env = ResourceEvent._dict_to_env(value, new_key + ".", env)
            else:
                env[new_key] = str(value)

        return env

    def create_environment(self):
        return ResourceEvent._dict_to_env(self._event, "Event.", {})

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
            source_attributes['PhysicalResourceId'] = uuid.uuid4()

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
            log.error(u"Failed sending CloudFormation response: %s", str(e))