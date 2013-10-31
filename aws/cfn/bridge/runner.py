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
from threading import Thread
from Queue import Queue
import logging
import botocore.session
from aws.cfn.bridge.resources import Message, ResourceEvent, CustomResource

log = logging.getLogger("cfn.resourcebridge")


class CfnBridge(object):
    def __init__(self, custom_resources, num_threads=None):
        # Lookup of queue to resources
        self._resource_lookup = {}

        # Construct an unbounded Queue to hold our pending tasks
        self._task_queue = Queue()

        # List of queues already being polled.
        queues = set()

        # Build our resource lookup and queue list
        for new_res in custom_resources:
            # Generate a lookup key for the custom_resource
            lookup = LookupKey((new_res.queue_url, new_res.service_token, new_res.resource_type))

            # Check if there is an existing resource that already maps exactly to this resource.
            existing_res = self._resource_lookup.get(lookup)
            if existing_res:
                raise ValueError(u"[%s] section in '%s' handles the same events as [%s] in '%s'" %
                                (new_res.name, new_res.source_file, existing_res.name, existing_res.source_file))

            # Add our resource into the lookup
            self._resource_lookup[lookup] = new_res

            # Determine if this queue has been setup for polling
            if new_res.queue_url not in queues:
                queues.add(new_res.queue_url)
                # Construct a task to poll the new queue
                self._task_queue.put(QueuePollTask(new_res.queue_url, new_res.region, self._resource_lookup))

        # Determine the maximum number of threads to use
        count = len(custom_resources)
        self._num_threads = num_threads if num_threads else count + min(count * 3, 10)

        # Display a warning if polling/processing threads will be shared (meaning we can't poll & work)
        if self._num_threads <= count:
            log.warn(u"You have %s custom resource(s) and %s thread(s). There may be degraded performance "
                     u"as polling threads will have to be shared with processing threads.", count, self._num_threads)

    def process_messages(self):
        for i in range(self._num_threads):
            worker = Thread(target=self.task_worker)
            worker.daemon = True
            worker.start()

    def task_worker(self):
        while True:
            task = self._task_queue.get()
            try:
                new_tasks = task.execute_task()
                if new_tasks:
                    for t in new_tasks:
                        self._task_queue.put(t)
            except:
                log.exception(u"Failed executing task")
            finally:
                self._task_queue.task_done()

                # Reschedule the polling tasks
                if isinstance(task, QueuePollTask):
                    self._task_queue.put(task)


class LookupKey(object):
    def __init__(self, properties_tuple):
        self._properties = properties_tuple

    @property
    def properties(self):
        return self._properties

    def __eq__(self, other):
        return self.properties == other.properties

    def __hash__(self):
        return hash(self._properties)

    def __repr__(self):
        return str(self._properties)


class BaseTask(object):
    def execute_task(self):
        pass


class QueuePollTask(BaseTask):
    def __init__(self, queue_url, region, custom_resource_lookup):
        self._queue_url = queue_url
        self._region = region
        self._resource_lookup = custom_resource_lookup

    def retrieve_events(self, max_events=1):
        """Attempts to retrieve events from the provided SQS queue"""
        session = botocore.session.get_session()
        sqs = session.get_service("sqs")
        receive = sqs.get_operation("ReceiveMessage")
        http_response, response_data = receive.call(sqs.get_endpoint(self._region),
                                                    queue_url=self._queue_url,
                                                    wait_time_seconds=20,
                                                    max_number_of_messages=max_events)

        # Swallow up any errors/issues, logging them out
        if http_response.status_code != 200 or not "Messages" in response_data:
            log.error(u"Failed to retrieve messages from queue %s with status_code %s: %s" %
                      (self._queue_url, http_response.status_code, response_data))
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

    def _find_resource(self, queue_url, service_token, resource_type):
        lookup = LookupKey((queue_url, service_token, resource_type))
        log.debug(u"Trying to locate find resource for %s", lookup)
        return self._resource_lookup.get(lookup)

    def execute_task(self):
        log.debug(u"Checking queue %s", self._queue_url)
        events = self.retrieve_events()

        tasks = []
        for event in events:
            service_token = event.get('ServiceToken')
            resource_type = event.get('ResourceType')

            # Try to locate a handler for our event, starting with most specific lookup first
            resource = self._find_resource(self._queue_url, service_token, resource_type)
            if not resource:
                resource = self._find_resource(self._queue_url, None, resource_type)
            if not resource:
                resource = self._find_resource(self._queue_url, service_token, None)
            if not resource:
                resource = self._find_resource(self._queue_url, None, None)

            # Handle the event using the found resource
            if resource:
                event.increase_timeout(resource.determine_event_timeout(event))
                tasks.append(ResourceEventTask(resource, event))
            else:
                # No handler, log an error and leave the message on the queue.
                log.error(u"Unable to find handler for Event from %s with ServiceToken(%s) and ResourceType(%s); "
                          u"event will be left on queue" %
                          (self._queue_url, service_token, resource_type))
                log.debug(u"Unhandled event: %s", event)
                log.debug(u"Registered handlers: %s", list(self._resource_lookup.iterkeys()))

        return tasks


class ResourceEventTask(BaseTask):
    def __init__(self, custom_resource, event):
        self._custom_resource = custom_resource
        self._event = event

    def execute_task(self):
        log.debug(u"%s: Executing task for event %s" % (self._custom_resource.name, self._event))
        self._custom_resource.process_event(self._event)
        self._event.delete()
        return []
