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

from collections import namedtuple
from lxml.etree import Element, XMLSchema, XMLParser, fromstring  # nosec - parsed xml is checked if there are no DOCTYPE elements. We don't use features that introduce other vulnerabilities
from lxml.isoschematron import Schematron  # nosec - parsed xml is tested against DOCTYPE elements, we don't use features that introduce other vulnerabilities

from . import utils
from .FileOpener import open_file
from .LibException import LibException, XmlValidationFailedException
from .LibConfig import LibConfig


class SecureXmlParser:
    """
    Class for securely loading xmls - this involves checking if there are !DOCTYPE declarations
    and discarding such xmls and using lxml module for loading xmls. We also validate xmls to be loaded with
    a schema if a schema is specified.
    """
    class Schema:
        SchemaType = namedtuple('SchemaType', 'path, xml_schema, schematron')

        Ibst = SchemaType('schema.xsd', xml_schema=True, schematron=True)
        Layout = SchemaType('schema/layout_schema.xsd', xml_schema=True, schematron=False)
        UserXml = SchemaType('schema/user_xml_schema.xsd', xml_schema=True, schematron=False)
        NoSchema = None
        PluginXml = SchemaType('schema/plugin_schema.xsd', xml_schema=True, schematron=False)

    def __init__(self, xml_path: str, schema: Schema):
        self.xml_path = xml_path
        self.schema = schema
        self._xml_file_content = None
        self._xml_root = None
        self._schema_xml_root = None
        self._xml_parser = XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_comments=True,
                                     encoding='UTF8')

    @property
    def xml_file_content(self) -> str:
        if self._xml_file_content is None:
            utils.check_file_path(self.xml_path, can_be_empty=False, throwing=True)
            with open_file(self.xml_path, 'r', encoding='UTF8') as f:
                self._xml_file_content = f.read()
        return self._xml_file_content

    @property
    def xml_root(self) -> Element:
        if self._xml_root is None:
            self._xml_root = fromstring(self.xml_file_content.encode('utf8'), self._xml_parser)   # nosec - parsed xml is tested against DOCTYPE elements, we don't use features that introduce other vulnerabilities
            if self.schema is not self.Schema.NoSchema and not LibConfig.skipSchemaValidation:
                self.validate_xml_tree()
        return self._xml_root

    @property
    def schema_path(self) -> str:
        if self.schema is self.Schema.NoSchema:
            raise LibException('Tried to get full path to schema while schema has not been set at all.')
        return os.path.abspath(os.path.join(LibConfig.appDir, self.schema.path))

    @property
    def schema_xml_root(self) -> Element:
        if self._schema_xml_root is None:
            with open_file(self.schema_path, 'r') as f:
                schema_content = f.read()
                self._schema_xml_root = fromstring(schema_content.encode('utf8'), self._xml_parser)   # nosec - parsed xml is tested against DOCTYPE elements, we don't use features that introduce other vulnerabilities
        return self._schema_xml_root

    @classmethod
    def protect_plugins_dirs(cls, dir_paths: list):
        """Protects the tool from XML attacks, i.e. check if there are any DOCTYPE elements (we forbid it)."""
        for dir_path in dir_paths:
            for root_dir, _, files in os.walk(dir_path):
                mxmls = [file for file in files if '.mxml' == os.path.splitext(file)[1]]
                for file in mxmls:
                    _ = cls(os.path.join(root_dir, file), cls.Schema.NoSchema).xml_root

    def validate_xml_tree(self):
        """Validates xml based on xml scheme and / or schematron included to source."""
        if self.schema.xml_schema:
            schema_validator = XMLSchema(self.schema_xml_root)
            self.validate_with(schema_validator)

        if self.schema.schematron:
            schematron_validator = Schematron(etree=self.schema_xml_root, error_finder=Schematron.ASSERTS_AND_REPORTS)
            self.validate_with(schematron_validator)

    def validate_with(self, validator):
        result = validator.validate(self.xml_root)
        if not result:
            log = validator.error_log
            raise XmlValidationFailedException(os.path.abspath(self.xml_path), self.schema_path,
                                               log.last_error.message, log.last_error.line)
