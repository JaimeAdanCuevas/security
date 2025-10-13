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
from .IOutputManifestsFunction import IOutputManifestsFunction
from ...Converter import Converter
from ...FileManager import FileManager
from ...LibException import ComponentAttributeException
from ...SecureXmlParser import SecureXmlParser
from ...structures import ValueWrapper


class UpdateManifestFunction(IOutputManifestsFunction):

    ExportSettingsNodeName = './/export'
    ImportSettingsNodeName = './/import'
    ManifestBinarySettingName = 'manifest_binary'
    ManifestHashSettingName = 'manifest_hash'
    PublicKeyHashSettingName = 'public_key_hash'
    PostPvSettingName = 'post_pv'

    def __init__(self, xml_node, **kwargs):
        self.import_xml = None
        super().__init__(xml_node, **kwargs)

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        import_xml_node = self._parse_node(xml_node, self.Tags.IMPORT_XML_NODE)
        self.import_xml = ValueWrapper(import_xml_node, self)

    def _build(self, buffer):
        manifest_hash = self._get_manifest_hash(buffer)
        public_key_hash = self._get_public_key_hash(buffer)
        root = SecureXmlParser(self.import_xml.value, SecureXmlParser.Schema.Ibst).xml_root
        import_file_node = root.find(self.ImportSettingsNodeName)
        if import_file_node is not None:
            try:
                file = import_file_node[0]
                if file.attrib['name'] == self.ManifestBinarySettingName:
                    file.attrib['value'] = self.output.value
            except KeyError as ex:
                raise ComponentAttributeException(f'Wrong attribute {ex} in {self.import_xml.value}') from None
        export = root.find(self.ExportSettingsNodeName)
        for child in export:
            try:
                if child.attrib['name'] == self.ManifestHashSettingName:
                    child.attrib['value'] = Converter.bytes_to_string(manifest_hash)
                elif child.attrib['name'] == self.PostPvSettingName:
                    child.attrib['value'] = str(self.post_pv.value)
                elif child.attrib['name'] == self.PublicKeyHashSettingName:
                    child.attrib['value'] = Converter.bytes_to_string(public_key_hash)
            except KeyError as ex:
                raise ComponentAttributeException(f'Wrong attribute {ex} in {self.import_xml.value}') from None
        FileManager.save_xml_file(self.import_xml.value, root)
