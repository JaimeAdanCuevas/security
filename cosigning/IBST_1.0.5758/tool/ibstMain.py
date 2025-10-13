#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2022 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

import os
import copy

from .IbstCommandLineOptions import IbstCommandLineOptions
from .BinaryGenerator import BinaryGenerator
from .LibException import LibException, ComponentException, FunctionException
from .exceptions import GeneralException
from .utils import get_file_name_no_ext, print_header, is_python_ver_satisfying
from .components.IComponent import IComponent
from .LibConfig import LibConfig
from .PathResolver import PathResolver
from .SecureXmlParser import SecureXmlParser
from .ColorPrint import ColorPrint


def print_info(input_name, command_line_options):
    if command_line_options.output_file:
        output_path = os.path.abspath(command_line_options.output_file)
        print("{} binary created: {}".format(input_name, output_path))


def main(appfilepath=__file__, input_args=None):
    LibConfig.toolType = LibConfig.ToolType.Ibst
    appfilename = os.path.basename(appfilepath)
    LibConfig.appDir = os.path.split(os.path.abspath(appfilepath))[0]
    name = '\nIntel (R) IBST - Image Building and Signing Tool. '
    version = '1.0.3864'
    print_header(name=name, version=version, copyright_date_range="2015-2022")
    if not is_python_ver_satisfying(required_python=(3, 6)):
        LibConfig.exitCode = -1
        return LibConfig.exitCode

    # If IBST was loaded as module it happen that appfilepath doesn't point to ibst.py but to this file: ibstMain.py
    # But schema.xsd is next to ibst.py, therefore we need to change the path to schema
    xml_parser = SecureXmlParser(None, SecureXmlParser.Schema.Ibst)
    if not os.path.exists(xml_parser.schema_path) and appfilepath == __file__:
        ColorPrint.warning('Could not find {}'.format(xml_parser.schema_path))
        SecureXmlParser.Schema.Ibst = SecureXmlParser.Schema.SchemaType(os.path.join('..',
                                                                                     SecureXmlParser.Schema.Ibst.path),
                                                                        SecureXmlParser.Schema.Ibst.xml_schema,
                                                                        SecureXmlParser.Schema.Ibst.schematron)
        xml_parser = SecureXmlParser(None, SecureXmlParser.Schema.Ibst)
        ColorPrint.warning('Changed path to schema to: {}'.format(xml_parser.schema_path))

    LibConfig.settingsTag = 'settings'
    LibConfig.overridesTag = 'ibst_overrides'
    LibConfig.defaultPaddingValue = IComponent.AlignByte.Byte00
    LibConfig.rootTag = 'ibst'
    LibConfig.maxBufferSize = 128 * 1024 * 1024

    command_line_options = IbstCommandLineOptions(appfilename, LibConfig.appDir, input_args)
    input_name = get_file_name_no_ext(command_line_options.input_file)
    path_resolver = PathResolver(LibConfig.appDir)
    try:
        override_nodes = []
        if command_line_options.config_override_file is not None:
            override_nodes = BinaryGenerator.get_override_nodes(command_line_options.config_override_file)
        schema = SecureXmlParser.Schema.NoSchema if command_line_options.skip_validation else SecureXmlParser.Schema.Ibst
        if override_nodes:
            for override_node in override_nodes:
                cli_opt_copy = copy.deepcopy(command_line_options)
                generator = BinaryGenerator(cli_opt_copy.input_file, schema, path_resolver)
                generator.apply_nodes_override(override_node)
                generator.process_build(cli_opt_copy, input_name)
                print_info(input_name, cli_opt_copy)
        else: 
            generator = BinaryGenerator(command_line_options.input_file, schema, path_resolver)
            generator.process_build(command_line_options, input_name)
            print_info(input_name, command_line_options)
    except (LibException, ComponentException, FunctionException, GeneralException) as ex:
        print("Failed to build image, an error occured: {}".format(ex))
        LibConfig.exitCode = -1
    return LibConfig.exitCode
