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
import os
import ConfigParser
import logging

from .resources import CustomResource

# Construct a logger to write messages about bridges
log = logging.getLogger("cfn.resourcebridge")


def _parse_config(config_file):
    """Parses the provided configuration; returns list of sections

    When provided with a valid configuration file, will load all of the sections and return a list of
    CustomResources that match the provided configuration. It is assumed the file was already checked
    for existence before being passed in.
    """
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    resources = []
    for resource_name in config.sections():
        # Convert configuration options into dictionary (lowercasing all keys)
        options = dict((i[0].lower(), i[1]) for i in config.items(resource_name))

        # Construct a new CustomResource with the provided configuration
        resources.append(CustomResource(resource_name, config_file, options))

    return resources


def _parse_configurations(config_files):
    """Parses the provided configurations; returns a list of CustomResources

    Iterates over the list of configuration files and creates a list of CustomResources matching
    the sections in the configurations. It is assumed the files were already checked for existence.
    """
    resources = []
    # Iterate through the config files and try to parse them
    for bridge_file in config_files:
        # Attempt to parse the configuration
        resources += _parse_config(bridge_file)

    return resources


def load_resources_from_configuration(config_dir):
    """Locates and parses configuration files

    Given a configuration directory, reads in the cfn-resource-bridge.conf file
    and any configurations under the bridge.d/ directory. It requires at least
    one configuration file to exist.
    """
    config_file = os.path.join(config_dir, 'cfn-resource-bridge.conf')
    bridge_files = []

    # Add the default configuration file if it exists
    if os.path.isfile(config_file):
        bridge_files.append(config_file)

    # Add any bridge hook files, if they exist
    bridges_dir = os.path.join(config_dir, 'bridge.d')
    if os.path.isdir(bridges_dir):
        for hook_file in os.listdir(bridges_dir):
            if os.path.isfile(os.path.join(bridges_dir, hook_file)) and hook_file.endswith('.conf'):
                bridge_files.append(os.path.join(bridges_dir, hook_file))

    # If we can't find any bridge files, error out.
    if not bridge_files:
        raise ValueError(u"Could not find default configuration file, %s, or additional"
                         u" configurations in the %s directory"
                         % (config_file, bridges_dir))

    # Load our configurations and get the custom resource definitions
    resources = _parse_configurations(bridge_files)

    # Fail if we have not found any custom resources.
    if not resources:
        raise ValueError(u"No resources were defined in (%s)" % bridge_files)

    return resources