#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

import os
from typing import Set

from .FileManager import FileManager
from .MapGenerator import MapGenerator, XmlMapFormatter, XmlInfoFormatter
from .components.ComponentFactory import ComponentFactory
from .components.IComponent import IComponent
from .LibException import LibException, ComponentException, FileException, BinaryGeneratorException
from .utils import get_file_name_no_ext, get_file_ext
from .SecureXmlParser import SecureXmlParser
from .structures import Buffer
from .LibConfig import LibConfig
from .PathResolver import PathResolver


class BinaryGenerator:
    class Tags:
        VERSION = "version"
        COSIGN = "cosign"

    buildOptsTag = None  # overridden in __init__
    minSizeToSave = 128

    max_size = None
    xml_root = None
    root_component = None
    layout_root = None
    configuration_root = None
    decomp_root = None
    buffer = None

    def __init__(self, xml_config_file, schema: SecureXmlParser.Schema, path_resolver: PathResolver = None,
                 component_factory=ComponentFactory):
        BinaryGenerator.buildOptsTag = LibConfig.settingsTag
        try:
            FileManager.validate_path_to_open(xml_config_file)
        except FileException as ex:
            raise BinaryGeneratorException('Could not load binary generator.\n' + ex.message) from None
        self.xml_name = xml_config_file
        self.schema = schema
        self.xml_root = SecureXmlParser(xml_config_file, schema).xml_root
        if path_resolver:
            path_resolver.resolve_paths(self.xml_root, LibConfig.settingsTag)

        self.max_size = LibConfig.maxBufferSize
        self.xml_config_file = xml_config_file
        self.map_gen = MapGenerator(XmlMapFormatter)
        self.component_factory_cls = component_factory

    def switch_xml(self, xml_config_file, path_resolver: PathResolver = None):
        self.xml_name = xml_config_file
        self.xml_root = SecureXmlParser(xml_config_file, self.schema).xml_root
        if path_resolver:
            path_resolver.resolve_paths(self.xml_root, LibConfig.settingsTag)
        self.xml_config_file = xml_config_file

    @staticmethod
    def get_override_nodes(overrides_file):
        if not os.path.isfile(overrides_file):
            raise LibException(f"No such fle: '{overrides_file}'")

        override_root = SecureXmlParser(overrides_file, SecureXmlParser.Schema.NoSchema).xml_root
        if override_root.tag != LibConfig.overridesTag:
            raise LibException(f"Invalid config override file - override_root node should be "
                               f"'{LibConfig.overridesTag}'")
        cosign_nodes = override_root.findall(BinaryGenerator.Tags.COSIGN)
        if cosign_nodes:
            return cosign_nodes
        return [override_root]

    def apply_nodes_override(self, override_root):
        settings_node = self.xml_root.find(self.buildOptsTag)
        if settings_node is None:
            raise LibException(f"Invalid configuration file: missing '{self.buildOptsTag}' node")

        for override_node in override_root:
            override_name = IComponent.get_name(override_node)
            xml_nodes = settings_node.findall(override_node.tag)

            for xml_node in xml_nodes:
                if override_name == IComponent.get_name(xml_node):
                    settings_node.remove(xml_node)
                    break

            settings_node.append(override_node)

    def _get_substitution_src_nodes(self):
        settings_node = self.xml_root.find(self.buildOptsTag)
        if settings_node is None:
            raise LibException(f"Invalid configuration file: missing '{self.buildOptsTag}' node")
        return settings_node.findall('node')

    def _substitute_target_nodes(self, nodes):
        for node in nodes:
            node_name = node.attrib[IComponent.Tags.NAME]
            dst_nodes = self.xml_root.findall('.//' + node_name)
            if len(dst_nodes) != 1:
                raise LibException("Substituted nodes need to be unique")
            dst_node = dst_nodes[0]
            dst_node.clear()
            dst_node.extend(node.getchildren())
            print(f"Overriding {node_name} component")

    def _substitute_nodes(self):
        nodes = self._get_substitution_src_nodes()
        self._substitute_target_nodes(nodes)

    @staticmethod
    def split_override(override):
        parts = override.split("=")
        if len(parts) != 2:
            raise LibException(f"Invalid option '{override}', use syntax: <setting_name>=<value>")
        path = parts[0]
        path_parts = path.split(LibConfig.pathSeparator)
        value = parts[1]
        return path, path_parts, value

    def apply_cmd_overrides(self, overrides) -> Set[IComponent]:
        """Applies overrides to components."""
        overriden_settings: Set[IComponent] = set()
        for override in overrides:
            path, path_parts, value = self.split_override(override)

            current_component = self.configuration_root
            for path_part in path_parts:
                try:
                    current_component = current_component.get_child(path_part)
                except ComponentException as e:
                    raise LibException(f"Invalid override path: {path}, {e}") from None

            current_component.parse_string_value(value)
            current_component.validate()
            current_component.validate_during_overriding()
            current_component.is_overwritten = True
            overriden_settings.add(current_component)

        return overriden_settings

    def apply_overrides(self, overrides):
        """Applies overrides to xml."""
        for override in overrides:
            path, path_parts, value = self.split_override(override)

            xml_node = self.xml_root.find(self.buildOptsTag)
            if xml_node is None:
                raise LibException(f"Invalid configuration file: missing '{self.buildOptsTag}' node")

            for path_part in path_parts:
                # flat setting search
                child_node = xml_node.find(f"*[@name='{path_part}']")

                # group setting search
                if child_node is None:
                    child_node = xml_node.find(f".//*[@name='{path_part}']")

                # node search
                if child_node is None:
                    child_node = xml_node.find(path_part)

                if child_node is None:
                    raise LibException(f"Invalid path: '{path}', node '{xml_node.tag}' "
                                       f"doesn't have child '{path_part}'")
                xml_node = child_node

            xml_node.attrib[IComponent.Tags.VALUE] = value

    def _set_root_component(self, skip_calculates: bool = False):
        self.root_component = self.component_factory_cls().create_root_component(self.xml_root,
                                                                                 skip_calculates=skip_calculates)

    def parse_configuration(self, skip_calculates: bool = False):
        self._set_root_component(skip_calculates)
        self.configuration_root = self.root_component.get_child(self.buildOptsTag)
        self.root_component.initialize_defaults()

    def parse_decomposition(self):
        self.parse_root_child(LibConfig.decompositionTag)

    def decomposition_node_exists(self):
        return self.xml_root.find(LibConfig.decompositionTag) is not None

    def parse_layout(self):
        self.parse_decomposition()
        self.parse_root_child(LibConfig.layoutTag)
        self.layout_root = self.root_component.get_child(LibConfig.layoutTag)

    def parse_build_nodes(self, skip_calculates: bool = False):
        self.layout_root = self.parse_root_child(LibConfig.layoutTag, skip_calculates=skip_calculates)

    def parse_for_region_decomposition(self):
        self.parse_root_child(LibConfig.decompositionTag, skip_calculates=True)
        self.layout_root = self.parse_root_child(LibConfig.layoutTag, skip_calculates=True)

    def parse_root_child(self, node_name: str, skip_calculates: bool = False):
        node = self.xml_root.find(node_name)
        if node is not None and self.root_component:
            self.root_component.remove_child(node_name)
            factory = self.component_factory_cls()
            factory.root = self.root_component
            return factory.create_component(node, parent=self.root_component, skip_calculates=skip_calculates)
        return None

    def add_child_to_root(self, child: IComponent):
        self.root_component.remove_child(child.name)
        self.root_component.children.append(child)
        self.root_component.children_by_name[child.name] = child

    def build_layout(self, clear_build_settings=False):
        buffer = Buffer(-1, self.max_size)
        self.root_component.clear_data()
        self.layout_root.build_layout(buffer, clear_build_settings)

    def build(self):
        self.buffer = Buffer(-1, 1 if self.layout_root.size == 0 else self.layout_root.size)
        self.buffer.write(b'\xff' * self.layout_root.size)
        self.buffer.seek(0)
        self.layout_root.build(self.buffer)
        self.buffer = self.buffer.reduce_buffer_to_match_content()

    def save(self, file_path, start=None, end=None):
        """
        Saves current buffer as binary file

        Note: Can optionally specify offsets, but both values must be given.
        :param file_path: destined file path
        :param start: start offset (optional)
        :param end: end offset (optional)
        """
        start = start if start is not None else 0
        end = end if end is not None else self.buffer.tell()
        FileManager.save_binary_file(file_path, self.buffer[start:end])

    def save_info(self, file_path, save_components_to_binary=False):
        try:
            layout_node = self.root_component.get_child(LibConfig.layoutTag)
        except ComponentException as ex:
            print(f"Cannot save info/map - {str(ex)}")
            return None

        file_path = os.path.abspath(file_path)
        root_directory, ext = os.path.splitext(file_path)
        file_path = self.map_gen.generate_map(layout_node, root_directory, ext)
        if save_components_to_binary:
            self.save_components(layout_node, root_directory)
        return file_path

    def save_components(self, root: IComponent, directory):
        for child in root.children:
            self._save_component_to_file(child, directory)

    def _save_component_to_file(self, component: IComponent, directory):
        if not component.size or (component.size and component.size < self.minSizeToSave):
            return

        file_name = component.name
        if component.encryption_key_component:
            file_name += ".encrypted"
        file_name += ".bin"

        FileManager.save_binary_file(os.path.join(directory, file_name), component.get_bytes())
        directory = os.path.join(directory, component.name)
        for child in component.children:
            self._save_component_to_file(child, directory)

    def get_output_name(self, command_line_options):
        # check if output_name is defined in settings
        xml_node = self.xml_root.find(self.buildOptsTag)
        if xml_node is None:
            raise LibException(f"Invalid configuration file: missing '{self.buildOptsTag}' node")
        children_node = [node for node in xml_node
                         if IComponent.Tags.NAME in node.attrib
                         and node.attrib[IComponent.Tags.NAME] == "output_name"]
        if children_node and children_node[0].attrib[IComponent.Tags.VALUE]:
            return children_node[0].attrib[IComponent.Tags.VALUE]

        # if we are in decomposition mode set output file based on decomposed file name
        xml_node = self.xml_root.find(LibConfig.decompositionTag)
        if xml_node is not None:
            decomp_component = self.root_component.get_child(LibConfig.decompositionTag)
            if decomp_component.is_enabled() and decomp_component.output_suffix:
                file_name = xml_node.get('file')
                file_name = decomp_component.calculate_value(file_name, allow_calculate=True)
                file_ext = get_file_ext(file_name)
                file_name = file_name[:-len(file_ext)]
                return os.path.join(command_line_options.app_dir, file_name + decomp_component.output_suffix + file_ext)

        # set output file name based on input xml
        input_name = get_file_name_no_ext(command_line_options.input_file)
        return os.path.join(command_line_options.app_dir, input_name + '.bin')

    def process_build(self, command_line_options, input_name):
        self.apply_overrides(command_line_options.setting_overrides)
        self._substitute_nodes()
        self.parse_configuration()
        self.parse_layout()
        self.build_layout()
        self.build()
        if not command_line_options.output_file and (LibConfig.generateOutput or LibConfig.generateOutput is None):
            output = self.get_output_name(command_line_options)
            command_line_options.output_file = output
        if command_line_options.output_file:
            self.save(command_line_options.output_file)

        if command_line_options.output_info:
            info_path = os.path.abspath(command_line_options.output_info)
            self.map_gen.formatter = XmlInfoFormatter
            final_info_path = self.save_info(file_path=info_path, save_components_to_binary=True)
            print(f"{input_name} info created: {final_info_path}")

        if not command_line_options.output_map and command_line_options.output_file:
            file_name = command_line_options.output_file
            file_name = file_name[:-len(get_file_ext(file_name))]
            command_line_options.output_map = f"{file_name}_map"

        if command_line_options.output_map:
            self.map_gen.formatter = XmlMapFormatter
            map_path = os.path.abspath(command_line_options.output_map)
            final_map_path = self.save_info(file_path=map_path)
            print(f"{input_name} map created: {final_map_path}")
