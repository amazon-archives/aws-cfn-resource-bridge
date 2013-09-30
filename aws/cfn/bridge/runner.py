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
from threading import Thread
from Queue import Queue
import logging

log = logging.getLogger("cfn.resourcebridge")


#
# TODO: Evaluate the threading model. There are several approaches we can take here.
#       I've currently gone with a shared thread pool, with an "unlimited" work queue. However,
#       since it is shared, polling will slow (and eventually pause) if the backlog gets too
#       large.
class CfnBridge(object):
    def __init__(self, custom_resources, num_threads=None):
        self.custom_resources = custom_resources

        # Determine the maximum number of threads to use
        count = len(custom_resources)
        self.num_threads = count + min(count * 3, 10) if not num_threads else num_threads

        # Display a warning if polling/processing threads will be shared (meaning we can't poll & work)
        if self.num_threads <= count:
            log.warn(u"You have %s custom resource(s) and %s thread(s). There may be degraded performance "
                     u"as polling threads will have to be shared with processing threads.", count, self.num_threads)

        # Construct an unbounded Queue and add our initial poll tasks on.
        self.task_queue = Queue()
        for resource in self.custom_resources:
            self.task_queue.put(QueuePollTask(resource))

    def process_messages(self):
        for i in range(self.num_threads):
            worker = Thread(target=self.task_worker)
            worker.daemon = True
            worker.start()

    def task_worker(self):
        while True:
            task = self.task_queue.get()
            try:
                new_tasks = task.execute_task()
                if new_tasks:
                    for t in new_tasks:
                        self.task_queue.put(t)
            except:
                log.exception(u"Failed executing task")
            finally:
                self.task_queue.task_done()

                # Reschedule the polling tasks
                if isinstance(task, QueuePollTask):
                    self.task_queue.put(task)


class BaseTask(object):
    def execute_task(self):
        pass


class QueuePollTask(BaseTask):
    def __init__(self, custom_resource):
        self._custom_resource = custom_resource

    def execute_task(self):
        log.debug(u"%s: Checking queue %s" % (self._custom_resource.name, self._custom_resource.queue_url))
        events = self._custom_resource.retrieve_events()

        tasks = []
        for event in events:
            # Increase the timeout of the message so other workers don't pull it down while processing
            event.increase_timeout(self._custom_resource.determine_event_timeout(event))

            tasks.append(ResourceEventTask(self._custom_resource, event))

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