#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2020-2024 Intel Corporation.
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

from lxml.etree import Element, SubElement  # nosec

from .IOutputManifestsFunction import IOutputManifestsFunction
from ...FileManager import FileManager
from ...LibConfig import LibConfig
from ...structures import ValueWrapper
from ..IComponent import IComponent
from ...ColorPrint import log


class ExportManifestsFunction(IOutputManifestsFunction):

    ImportManifestsSettingName = 'import_manifests'
    ValidateManifestsSettingName = 'validate_manifests'
    OutputManifestsSettingName = 'output_name'
    ManifestsSettingName = 'manifests'
    ValidManifestHeaderTypeName = 'valid_manifest_header_type'

    def __init__(self, xml_node, **kwargs):
        self.manifest_function_node = xml_node
        self.import_xml_root = None
        self.manifests_setting_node = None
        self.load_data_component: ValueWrapper = None
        super().__init__(xml_node, **kwargs)

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        load_data_node = self._parse_node(xml_node, self.Tags.LOAD_DATA_NODE)
        self.load_data_component = ValueWrapper(load_data_node, self)

    def _build(self, buffer):
        # When only exporting manifests then we don't need any output
        if LibConfig.generateOutput is None:
            LibConfig.generateOutput = False
        super()._build(buffer)
        os.makedirs(self.output.value, exist_ok=True)
        self._initialize_import_xml()
        for manifest in self._find_manifests(buffer, self.output.value):
            self.manifests.append(manifest)
            if manifest.binary_path:
                self._save_manifest(manifest)
            manifest.to_xml_node(parent=self.manifests_setting_node)
        if self.manifests:
            self._save_input_xml()
            log().success(f'{len(self.manifests)} manifests exported to {os.path.abspath(self.output.value)}')
        else:
            log().warning('No manifest has been found.')
        self._move_buffer_to_end(buffer)

    @staticmethod
    def _save_manifest(manifest):
        FileManager.save_binary_file(manifest.binary_path, manifest.manifest)

    def _initialize_import_xml(self):
        self.import_xml_root = Element(LibConfig.rootTag)
        self._create_settings_node()
        self._create_layout_node()
        self._create_decomposition_node()

    def _create_settings_node(self):
        settings_node = SubElement(self.import_xml_root, LibConfig.settingsTag)
        SubElement(settings_node, 'file', {'name': 'binary_input', 'value': ''})
        SubElement(settings_node, 'number', {'name': self.ImportManifestsSettingName, 'value': '1'})
        SubElement(settings_node, 'number', {'name': self.ValidateManifestsSettingName, 'value': '1'})
        SubElement(settings_node, 'number', {'name': self.ValidManifestHeaderTypeName,
                                             'value': str(self.valid_manifest_header_type.value)})
        SubElement(settings_node, 'string', {'name': self.OutputManifestsSettingName, 'value': 'imported.bin'})
        self.manifests_setting_node = SubElement(settings_node, self.ManifestsSettingName)

    def _copy_manifest_function_node(self, tag, setting_to_enable):
        function_node = copy.deepcopy(self.manifest_function_node)
        function_node.tag = tag
        function_node.attrib[IComponent.Tags.ENABLED] = f'/{LibConfig.settingsTag}/{setting_to_enable}.value != 0'
        self._add_common_nodes(function_node)
        self._clear_xml_formatting(function_node)
        return function_node

    def _create_layout_node(self):
        layout_node = SubElement(self.import_xml_root, LibConfig.layoutTag)
        SubElement(layout_node, self.load_data_component.value.name,
                   {ValueWrapper.Tags.CALCULATE: self.load_data_component.value.value_formula})

        # Create nodes with validate and import functions
        function_import_node = self._copy_manifest_function_node('function_import_manifests',
                                                                 self.ImportManifestsSettingName)
        function_import_node.find(self.Tags.OUTPUT).attrib[ValueWrapper.Tags.CALCULATE] =\
            f'/{LibConfig.settingsTag}/binary_input.path'
        self._remove_nodes(function_import_node, [self.Tags.LOAD_DATA_NODE])
        layout_node.append(function_import_node)

        function_validate_node = self._copy_manifest_function_node('function_validate_manifests',
                                                                   self.ValidateManifestsSettingName)
        self._remove_nodes(function_validate_node, [self.Tags.OUTPUT, self.Tags.LOAD_DATA_NODE])
        layout_node.append(function_validate_node)

    def _add_common_nodes(self, manifests_function_node):
        SubElement(manifests_function_node,
                   self.Tags.MANIFEST_LIST,
                   attrib={ValueWrapper.Tags.CALCULATE: f'/{LibConfig.settingsTag}/{self.ManifestsSettingName}'})

    def _create_decomposition_node(self):
        decomposition_component = self.decomposition_node.value
        decomposition_node = copy.deepcopy(decomposition_component.decomposition_xml_node)
        self._clear_xml_formatting(decomposition_node)
        self.import_xml_root.append(decomposition_node)

    @staticmethod
    def _clear_xml_formatting(xml_node):
        # We need to clear text in and between nodes - if we don't then after 'pretty_printing'
        # there will be lot of empty lines
        for node in xml_node.iter():
            node.text = ''
            node.tail = ''

    @staticmethod
    def _remove_nodes(xml_node, node_names_to_remove):
        for node_name_to_remove in node_names_to_remove:
            node_to_remove = xml_node.find(node_name_to_remove)
            if node_to_remove is not None:
                xml_node.remove(node_to_remove)

    def _save_input_xml(self):
        xml_path = os.path.join(self.output.value, 'ImportManifests.xml')
        FileManager.save_xml_file(xml_path, self.import_xml_root)
