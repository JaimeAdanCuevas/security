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
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
import os
from typing import List

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
    versionAttribTag = "version"
    decompositionTag = "decomposition"
    cosignTag = "cosign"
    max_size = None

    xml_tree = None
    root_component = None
    layout_root = None
    configuration_root = None
    decomp_root = None
    buffer = None

    def __init__(self, xml_config_file, path_resolver: PathResolver=None):
        BinaryGenerator.buildOptsTag = LibConfig.settingsTag
        validate_file(xml_config_file)
        self.xml_name = xml_config_file
        self.xml_tree = Et.ElementTree(file=xml_config_file)
        if path_resolver:
            path_resolver.resolve_paths(self.xml_tree, LibConfig.settingsTag)

        self.max_size = LibConfig.maxBufferSize
        self.xml_config_file = xml_config_file
        self.is_gui = LibConfig.is_gui

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

    def parse(self):
        root = self.xml_tree.getroot()
        self.root_component = ComponentFactory().create_root_component(root)
        if not self.is_gui:
            self.layout_root = self.root_component.get_child(self.layoutTag)
        self.configuration_root = self.root_component.get_child(self.buildOptsTag)
        self.root_component.initialize_defaults()
        #self.create_map(self.decompositionTag)
        #self.create_map(self.settingsTag)

    def parse_layout_for_gui(self):
        if not self.is_gui:
            return
        self.parse_root_child(self.decompositionTag)
        self.parse_root_child(self.layoutTag)
        self.layout_root = self.root_component.get_child(self.layoutTag)

    def parse_build_nodes(self):
        self.layout_root = self.parse_root_child(self.layoutTag)
        #TODO: reloading decomposition is not so simple
        #self.parse_node(self.decompositionTag)

    def parse_root_child(self, node_name):
        root = self.xml_tree.getroot()
        node = root.find(node_name)
        if node and self.root_component:
            self.root_component.remove_child(node_name)
            factory = ComponentFactory()
            factory.root = self.root_component
            return factory.create_component(node, parent=self.root_component)

    def add_child_to_root(self, child: IComponent):
        self.root_component.remove_child(child.name)
        self.root_component.children.append(child)
        self.root_component.children_by_name[child.name] = child

    def build_layout(self, clear_build_settings=False):
        buffer = Buffer(-1, self.max_size)
        self.layout_root.build_layout(buffer, clear_build_settings)

    def build(self):
        self.buffer = Buffer(-1, self.max_size)
        self.buffer.write(b'\xff' * self.max_size)
        self.buffer.seek(0)
        self.layout_root.build(self.buffer)
        self.buffer = self.buffer.reduce_buffer_to_match_content()
        #self.create_map(self.layoutTag)

    def save(self, file_path):
        try:
            with open(file_path, "wb") as file:
                file.write(self.buffer[:self.buffer.tell()])
        except Exception as e:
            raise LibException("Failed to save a file: %s" % str(e))

    def save_info(self, file_path, max_level=None,
                  attributes=[IComponent.offsetTag, IComponent.sizeTag, IComponent.valueTag],
                  skip_empty=False):
        try:
            layout_node = self.root_component.get_child(self.layoutTag)
        except ComponentException as ex:
            print("Cannot save info/map - {}".format(str(ex)))
            return

        file_path = os.path.abspath(file_path)
        root_directory, ext = os.path.splitext(file_path)

        if not ext:
            file_path = file_path + '.xml'

        root = self._generate_info(component=layout_node, parent_node=None,
                                   directory=root_directory, max_level=max_level,
                                   attributes=attributes, skip_empty=skip_empty)
        ugly_xml_content = Et.tostring(root, 'utf-8')
        dom_xml = minidom.parseString(ugly_xml_content)
        pretty_xml_content = dom_xml.toprettyxml(indent="   ", encoding='utf-8')

        with open(file_path, 'wb') as file:
            file.write(pretty_xml_content)

        # return the real path where 'info' was saved because an extension might have been added
        return file_path

    def _generate_info(self, component, parent_node, directory, max_level, attributes, skip_empty):
        if parent_node is None:
            element = Element(component.name)
        else:
            element = SubElement(parent_node, component.name)

        if IComponent.offsetTag in attributes:
            element.attrib[component.offsetTag] = hex(component.offset)
        if IComponent.sizeTag in attributes:
            element.attrib[component.sizeTag] = hex(component.size)

        if component.encryption_key_component:
            if IComponent.valueTag in attributes:
                element.attrib[component.valueTag] = '(encrypted)'
                self._save_component_to_file(component, directory)
        elif component.children and (max_level is None or max_level > 0):
            for child in component.children:
                if child._is_enabled() and (not skip_empty or child.size > 0):
                    self._generate_info(component=child, parent_node=element,
                                        directory=os.path.join(directory, component.name),
                                        max_level=(max_level - 1 if max_level else max_level),
                                        attributes=attributes if type(child).__name__ != "Bit" else [
                                            IComponent.valueTag],
                                        skip_empty=skip_empty)
        elif IComponent.valueTag in attributes:
            if type(component).__name__ != "Bit" and component.size > 128:
                element.attrib[component.valueTag] = '({} bytes)'.format(component.size)
                self._save_component_to_file(component, directory)
            else:
                if type(component.value) is str:
                    str_value = component.get_value_string() \
                        .replace("&", "&amp;") \
                        .replace("<", "&lt;") \
                        .replace(">", "&gt;") \
                        .replace("\"", "&quot;") \
                        .replace("\0", "")
                    element.attrib[component.valueTag] = str_value
                else:
                    element.attrib[component.valueTag] = component.get_value_string()

        return element

    def _save_component_to_file(self, component, directory):
        file_name = component.name
        if component.encryption_key_component:
            file_name += ".encrypted"
        file_name += ".bin"

        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(os.path.join(directory, file_name), 'wb') as file:
            file.write(component.get_bytes())

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
            file_name = xml_node.get('file')
            file_name = decomp_component.calculate_value(file_name, allow_calculate=True)
            file_ext = get_file_ext(file_name)
            file_name = file_name[:-len(file_ext)]
            return os.path.join(command_line_options.app_dir, file_name + '_cosign' + file_ext)

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

        self.parse()
        self.build_layout()
        self.build()
        if not command_line_options.output_file:
            output = self.get_output_name(command_line_options)
            command_line_options.output_file = output
        self.save(command_line_options.output_file)

        if command_line_options.output_info:
            info_path = os.path.abspath(command_line_options.output_info)
            final_info_path = self.save_info(file_path=info_path)
            print("{} info created: {}".format(input_name, final_info_path))

        if not command_line_options.output_map:
            file_name = command_line_options.output_file
            file_name = file_name[:-len(get_file_ext(file_name))]
            command_line_options.output_map = file_name + "_map.xml"

        if command_line_options.output_map:
            map_path = os.path.abspath(command_line_options.output_map)
            final_map_path = self.save_info(file_path=map_path, max_level=1,
                                            attributes=[IComponent.offsetTag, IComponent.sizeTag],
                                            skip_empty=True)
            print("{} map created: {}".format(input_name, final_map_path))

    def create_map(self, nodeTag: str):
        name = os.path.splitext(os.path.basename(self.xml_name))[0]
        if nodeTag in self.root_component.children_by_name:
            self.create_map_for_node(self.root_component.children_by_name[nodeTag], f"{name}_{nodeTag}.map")

    def create_map_for_node(self, node, file_path):
        with open(file_path, "w") as file:
            file.write(f"{node.name} map: \n")
            node.add_map_entry(file, 0)
