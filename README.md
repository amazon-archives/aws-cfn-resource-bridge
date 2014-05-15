aws-cfn-resource-bridge
=======================

A custom resource framework for AWS CloudFormation

Installation
------------
Clone the repo and run the ```setup.py``` file in the root:

```
python setup.py install
```

You can also use the file to build an RPM:

```
python setup.py bdist_rpm
```

As well as ```python```, the resulting RPM will also depend on ```python-argparse```, ```python-botocore``` and ```python-daemon```, packaged as RPMs.

Usage
-----
The options for the ```cfn-resource-bridge``` script are shown below. The ```CONFIG_PATH``` needs to contain a file named ```cfn-resource-bridge.conf``` with the details of the incoming custom resources and commands to run.

```
usage: cfn-resource-bridge [-h] [-c CONFIG_PATH] [--no-daemon] [-v]
                           [-t THREADS]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_PATH, --config CONFIG_PATH
                        The configuration directory (default: /etc/cfn)
  --no-daemon           Do not daemonize
  -v, --verbose         Enables verbose logging
  -t THREADS, --threads THREADS
                        Configure the number of threads to use
```

Example config file:

```
[eip-lookup]
resource_type=Custom::EipLookup
queue_url=https://your-sqs-queue-url-that-is-subscribed-to-the-sns-topic-in-the-service-token
timeout=60
default_action=/home/ec2-user/lookup-eip.py
```

The config file ```cfn-resource-bridge.conf``` can contain multiple sections and each section can contain the following options:

 - ```queue_url``` - the URL of the queue to pull messages from.
 - ```default_action``` - the default action to perform when a message is received.
 - ```create_action``` - the action to perform when a ```Create``` message is received.
 - ```delete_action``` - the action to perform when a ```Delete``` message is received.
 - ```update_action``` - the action to perform when a ```Update``` message is received.
 - ```timeout``` - the default timeout for messages taken from the queue.
 - ```create_timeout``` - the message timeout for create actions.
 - ```delete_timeout``` - the message timeout for delete actions.
 - ```update_timeout``` - the message timeout for update actions.
 - ```flatten``` - flatten resource properties in environment variables (true by default).
 - ```service_token``` - optional service token for the event.
 - ```resource_type``` - the custom resource type.
 - ```region``` - the AWS region - only required if it can't be determined from the queue URL.
 
Contributing
-------------
1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request
