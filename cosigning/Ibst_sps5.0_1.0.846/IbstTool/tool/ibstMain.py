#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2019 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

import sys
import os
import copy

from .IbstCommandLineOptions import IbstCommandLineOptions
from .BinaryGenerator import BinaryGenerator
from .LibException import LibException, ComponentException, FunctionException
from .utils import get_file_name_no_ext
from .components.IComponent import IComponent
from .LibConfig import LibConfig
from .PathResolver import PathResolver


def print_info(input_name, command_line_options):
    output_path = os.path.abspath(command_line_options.output_file)
    print("{} binary created: {}".format(input_name, output_path))


def main(appfilepath=__file__, input_args=None):
    appfilename = os.path.basename(appfilepath)
    appfiledir = os.path.split(os.path.abspath(appfilepath))[0]
    version = '1.0.846'
    print('\nIntel (R) IBST - Image Building and Signing Tool. '
          'Version: {}\n'
          'Copyright (c) 2015-2019, Intel Corporation. All rights reserved.\n'.format(version))

    if sys.version_info[:2] < (3, 6):
        print('Python version 3.6 or greater is necessary to run.')
        return -1

    LibConfig.schemaPath = os.path.join(appfiledir, 'schema.xsd')
    # If IBST was loaded as module it happen that appfilepath doesn't point to ibst.py but to this file: ibstMain.py
    # But schema.xsd is next to ibst.py, therefore we need to change the path to schema
    if not os.path.exists(LibConfig.schemaPath) and appfilepath == __file__:
        print('Could not find {}'.format(LibConfig.schemaPath))
        LibConfig.schemaPath = os.path.join(os.path.split(appfiledir)[0], 'schema.xsd')
        print('Changed path to schema to: {}'.format(LibConfig.schemaPath))

    LibConfig.settingsTag = 'settings'
    LibConfig.overridesTag = 'ibst_overrides'
    LibConfig.defaultPaddingValue = IComponent.AlignByte.Byte00
    LibConfig.rootTag = 'ibst'
    LibConfig.maxBufferSize = 128 * 1024 * 1024

    command_line_options = IbstCommandLineOptions(appfilename, appfiledir, input_args)
    input_name = get_file_name_no_ext(command_line_options.input_file)
    path_resolver = PathResolver(appfiledir)
    try:
        override_nodes = []
        if command_line_options.config_override_file is not None:
            override_nodes = BinaryGenerator.get_override_nodes(command_line_options.config_override_file)
        if override_nodes:
            for override_node in override_nodes:
                cli_opt_copy = copy.deepcopy(command_line_options)
                generator = BinaryGenerator(cli_opt_copy.input_file, path_resolver)
                generator.apply_nodes_override(override_node)
                generator.process_build(cli_opt_copy, input_name)
                print_info(input_name, cli_opt_copy)
        else: 
            generator = BinaryGenerator(command_line_options.input_file, path_resolver)
            generator.process_build(command_line_options, input_name)
            print_info(input_name, command_line_options)
    except (LibException, ComponentException, FunctionException) as ex:
        print("Failed to build image, an error occured: {}".format(ex))
        return -1
