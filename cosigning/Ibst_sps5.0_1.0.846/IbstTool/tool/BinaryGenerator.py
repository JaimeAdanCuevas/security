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

import xml.etree.ElementTree as Et

import os
from typing import List

from .MapGenerator import MapGenerator, XmlMapFormatter, XmlInfoFormatter
from .components.ComponentFactory import ComponentFactory
from .components.IComponent import IComponent
from .LibException import LibException, ComponentException
from .utils import validate_file, validate_xml_str, get_file_name_no_ext, get_file_ext
from .structures import Buffer
from .LibConfig import LibConfig
from .PathResolver import PathResolver


class BinaryGenerator(object):
    layoutTag = "layout"
    buildOptsTag = None
    postBuildTag = "post_build"
    preBuildTag = "pre_build"
    versionAttribTag = "version"
    decompositionTag = "decomposition"
    cosignTag = "cosign"
    minSizeToSave = 128

    max_size = None
    xml_tree = None
    root_component = None
    layout_root = None
    configuration_root = None
    decomp_root = None
    buffer = None

    def __init__(self, xml_config_file, path_resolver: PathResolver = None, component_factory=ComponentFactory):
        BinaryGenerator.buildOptsTag = LibConfig.settingsTag
        validate_file(xml_config_file)
        self.xml_name = xml_config_file
        self.xml_tree = Et.ElementTree(file=xml_config_file)
        if path_resolver:
            path_resolver.resolve_paths(self.xml_tree, LibConfig.settingsTag)

        self.max_size = LibConfig.maxBufferSize
        self.xml_config_file = xml_config_file
        self.is_gui = LibConfig.is_gui
        self.map_gen = MapGenerator(XmlMapFormatter)
        self.component_factory_cls = component_factory

    def switch_xml(self, xml_config_file, path_resolver: PathResolver = None):
        self.xml_name = xml_config_file
        self.xml_tree = Et.ElementTree(file=xml_config_file)
        if path_resolver:
            path_resolver.resolve_paths(self.xml_tree, LibConfig.settingsTag)
        self.xml_config_file = xml_config_file

    @staticmethod
    def get_override_nodes(overrides_file):
        if not os.path.isfile(overrides_file):
            raise LibException("No such fle: '{}'".format(overrides_file))

        overrides_tree = Et.ElementTree(file=overrides_file)
        override_root = overrides_tree.getroot()
        if override_root.tag != LibConfig.overridesTag:
            raise LibException("Invalid config override file - override_root node should be '{}'"
                               .format(LibConfig.overridesTag))
        cosign_nodes = override_root.findall(BinaryGenerator.cosignTag)
        if cosign_nodes:
            return cosign_nodes
        return [override_root]

    def get_xml_root(self):
        return self.xml_tree.getroot()

    def apply_nodes_override(self, override_root):
        settings_node = self.xml_tree.getroot().find(self.buildOptsTag)
        if settings_node is None:
            raise LibException("Invalid configuration file: missing '{}' node"
                               .format(self.buildOptsTag))

        for override_node in override_root:
            override_name = IComponent.get_name(override_node)
            xml_nodes = settings_node.findall(override_node.tag)

            for xml_node in xml_nodes:
                if override_name == IComponent.get_name(xml_node):
                    settings_node.remove(xml_node)
                    break

            settings_node.append(override_node)

    def _get_substitution_src_nodes(self):
        settings_node = self.xml_tree.getroot().find(self.buildOptsTag)
        if settings_node is None:
            raise LibException("Invalid configuration file: missing '{}' node"
                               .format(self.buildOptsTag))
        return settings_node.findall('node')

    def _substitute_target_nodes(self, nodes):
        for node in nodes:
            node_name = node.attrib[IComponent.nameTag]
            dst_nodes = self.xml_tree.findall('.//' + node_name)
            if len(dst_nodes) != 1:
                raise LibException("Substituted nodes need to be unique")
            dst_node = dst_nodes[0]
            dst_node.clear()
            dst_node.extend(node.getchildren())
            print("Overriding {} component".format(node_name))

    def _substitute_nodes(self):
        nodes = self._get_substitution_src_nodes()
        self._substitute_target_nodes(nodes)

    @staticmethod
    def split_override(override):
        parts = override.split("=")
        if len(parts) != 2:
            raise LibException("Invalid option '{}', use syntax: <setting_name>=<value>"
                               .format(override))
        path = parts[0]
        path_parts = path.split(LibConfig.pathSeparator)
        value = parts[1]
        return path, path_parts, value

    """
        Applies overrides to components
    """

    def apply_cmd_overrides(self, overrides) -> List[IComponent]:
        overriden_settings: List[IComponent] = []
        for override in overrides:
            path, path_parts, value = self.split_override(override)

            current_component = self.configuration_root
            for path_part in path_parts:
                try:
                    current_component = current_component.get_child(path_part)
                except ComponentException as e:
                    raise LibException(f"Invalid override path: {path}, {e}")

            current_component.parse_string_value(value)
            current_component.validate()
            overriden_settings.append(current_component)

        return overriden_settings

    """
        Applies overrides to xml
    """

    def apply_overrides(self, overrides):
        for override in overrides:
            path, path_parts, value = self.split_override(override)

            xml_node = self.xml_tree.getroot().find(self.buildOptsTag)
            if xml_node is None:
                raise LibException("Invalid configuration file: missing '{}' node"
                                   .format(self.buildOptsTag))

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
                    raise LibException("Invalid path: '{}', node '{}' doesn't have child '{}'"
                                       .format(path, xml_node.tag, path_part))
                xml_node = child_node

            xml_node.attrib[IComponent.valueTag] = value

    def parse_configuration(self):
        root = self.xml_tree.getroot()
        self.root_component = self.component_factory_cls().create_root_component(root)
        self.configuration_root = self.root_component.get_child(self.buildOptsTag)
        self.root_component.initialize_defaults()

    def parse_layout(self):
        self.parse_root_child(self.decompositionTag)
        self.parse_root_child(self.layoutTag)
        self.layout_root = self.root_component.get_child(self.layoutTag)

    def parse_build_nodes(self):
        self.layout_root = self.parse_root_child(self.layoutTag)

    def parse_root_child(self, node_name):
        root = self.xml_tree.getroot()
        node = root.find(node_name)
        if node and self.root_component:
            self.root_component.remove_child(node_name)
            factory = self.component_factory_cls()
            factory.root = self.root_component
            return factory.create_component(node, parent=self.root_component)

    def add_child_to_root(self, child: IComponent):
        self.root_component.remove_child(child.name)
        self.root_component.children.append(child)
        self.root_component.children_by_name[child.name] = child

    def build_layout(self, clear_build_settings=False):
        buffer = Buffer(-1, self.max_size)
        self.root_component.clear_data()
        self.layout_root.build_layout(buffer, clear_build_settings)

    def build(self):
        self.buffer = Buffer(-1, self.max_size)
        self.buffer.write(b'\xff' * self.max_size)
        self.buffer.seek(0)
        self.layout_root.build(self.buffer)
        self.buffer = self.buffer.reduce_buffer_to_match_content()

    def save(self, file_path):
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(file_path))
        try:
            with open(file_path, "wb") as file:
                file.write(self.buffer[:self.buffer.tell()])
        except Exception as e:
            raise LibException("Failed to save a file: %s" % str(e))

    def save_info(self, file_path, save_components_to_binary=False):
        try:
            layout_node = self.root_component.get_child(self.layoutTag)
        except ComponentException as ex:
            print("Cannot save info/map - {}".format(str(ex)))
            return

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

        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(os.path.join(directory, file_name), 'wb') as file:
            file.write(component.get_bytes())
        directory=os.path.join(directory, component.name)
        for child in component.children:
            self._save_component_to_file(child, directory)

    def get_output_name(self, command_line_options):
        # check if output_name is defined in settings
        xml_node = self.xml_tree.getroot().find(self.buildOptsTag)
        if xml_node is None:
            raise LibException("Invalid configuration file: missing '{}' node"
                               .format(self.buildOptsTag))
        children_node = [node for node in xml_node
                         if IComponent.nameTag in node.attrib
                         and node.attrib[IComponent.nameTag] == "output_name"]
        if children_node and children_node[0].attrib[IComponent.valueTag]:
            return children_node[0].attrib[IComponent.valueTag]

        # if we are in decomposition mode set output file based on decomposed file name
        xml_node = self.xml_tree.getroot().find(self.decompositionTag)
        if xml_node is not None:
            decomp_component = self.root_component.get_child(self.decompositionTag)
            if decomp_component._is_enabled() and decomp_component.output_suffix:
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
        if not command_line_options.skip_validation:
            xml_txt = Et.tostring(self.xml_tree.getroot())
            if not validate_xml_str(xml_txt):
                raise LibException("Schema xml file validation failed")
        self.parse_configuration()
        self.parse_layout()
        self.build_layout()
        self.build()
        if not command_line_options.output_file:
            output = self.get_output_name(command_line_options)
            command_line_options.output_file = output
        self.save(command_line_options.output_file)

        if command_line_options.output_info:
            info_path = os.path.abspath(command_line_options.output_info)
            self.map_gen.formatter = XmlInfoFormatter
            final_info_path = self.save_info(file_path=info_path, save_components_to_binary=True)
            print("{} info created: {}".format(input_name, final_info_path))

        if not command_line_options.output_map:
            file_name = command_line_options.output_file
            file_name = file_name[:-len(get_file_ext(file_name))]
            command_line_options.output_map = file_name + "_map"

        if command_line_options.output_map:
            self.map_gen.formatter = XmlMapFormatter
            map_path = os.path.abspath(command_line_options.output_map)
            final_map_path = self.save_info(file_path=map_path)
            print("{} map created: {}".format(input_name, final_map_path))
