#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2020 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""


from ..LibException import ComponentException, ValueException
from .IComponent import IComponent
from ..Converter import Converter


class TableEntryComponent(IComponent):
    tableTag = "table"
    keyTag = "key"
    entry = None
    requiredTag = "required"
    table = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.table = self.calculate_value_from_path(self.table_path)
        # Not every entry could be found during init phase,
        # so exceptions are expected and second iteration will be needed
        self.entry = self._find_table_entry(self.table, False)

    def build(self, buffer):
        pass

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self.table_path = self._parse_attribute(xml_node, self.tableTag)
        self.key_query = self._parse_attribute(xml_node, self.keyTag)
        self.required = Converter.string_to_bool(
            self._parse_attribute(xml_node, self.requiredTag, required=False, default="True"))

    def build_layout(self, buffer, clear_build_settings=False):
        self.size = 0
        # If entry not found in init, try again while building
        if self.entry is None:
            self.entry = self._find_table_entry(self.table)
        if self.entry:
            self.children = self.entry.children
            self.children_by_name = self.entry.children_by_name
            self.index = self.entry.index
        self.enabled = self._is_enabled()

    def _should_omit_parsing(self, xml_node):
        return False

    def _is_enabled(self):
        if self.entry is None:
            self.enabled = False
        elif self.enabled_formula:
            self.enabled = super()._is_enabled()
        else:
            self.enabled = self.entry._is_enabled()
        return self.enabled

    def _find_table_entry(self, table, raise_if_not_found=True):
        # TODO: consider case when key is matched in more than one entry (Entry with lower index would be chosen)
        try:
            for entry in table.children:
                result = entry.calculate_value(self.key_query, allow_calculate=True)
                if type(result) is not bool:
                    raise ValueException(f"Key should be bool type, now is {type(result)}", result, self.name)
                if result:
                    return entry
            if self.required:
                raise ComponentException(
                    f"Could not find required entry with key '{self.key_query}'\nin table '{self.table_path}'",
                    self.name)
        except ComponentException:
            if raise_if_not_found:
                raise
