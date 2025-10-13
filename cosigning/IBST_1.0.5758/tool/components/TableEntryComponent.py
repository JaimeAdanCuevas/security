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

from ..LibException import ComponentException, ValueException
from .IComponent import IComponent
from ..Converter import Converter


class TableEntryComponent(IComponent):
    """Component used to get a table entry with specific value or properties. Two attributes have to be provided:
    * table - path to the table to search
    * key - a formula with conditions that match the searched entry

    This component is usually used in 'decomposition' section in order to extract some specific data
    (for example a partition with partition type equal to 2), here's an example:

    ```xml
    <layout>
        <byte_array name="table_pointers">
            <table_entry_pointer name="special_module_pointer" table="/decomposition/modules"
                                 key="this/module_type.value == 5" />
        </byte_array>
        <byte_array name="special_module"
                    calculate="/layout/table_pointers/special_module_pointer/some_bytes.value" />
    </layout>
    <decomposition file="/settings/input_file.path">
        <number name="entry_count" size="1" />
        <table name="modules" count="/decomposition/entry_count.value">
            <byte_array name="modules">
                <number name="module_type" size="1"/>
                <byte_array name="some_bytes" size="7" />
            </byte_array>
        </table>
    </decomposition>
    ```
    """

    class Tags(IComponent.Tags):
        TABLE = "table"
        KEY = "key"
        REQUIRED = "required"

    entry = None
    table = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.table = self.calculate_value_from_path(self.table_path)
        # Not every entry could be found during init phase,
        # so exceptions are expected and second iteration will be needed
        self.entry = self.find_table_entry(self.table, False)

    def build(self, buffer):
        pass

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self.table_path = self._parse_attribute(xml_node, self.Tags.TABLE)
        self.key_query = self._parse_attribute(xml_node, self.Tags.KEY)
        self.required = Converter.string_to_bool(
            self._parse_attribute(xml_node, self.Tags.REQUIRED, required=False, default="True"))

    def build_layout(self, buffer, clear_build_settings=False):
        self.size = 0
        # If entry not found in init, try again while building
        if self.entry is None:
            self.entry = self.find_table_entry(self.table)
        if self.entry:
            self.children = self.entry.children  # pylint: disable=attribute-defined-outside-init
            self.children_by_name = self.entry.children_by_name  # pylint: disable=attribute-defined-outside-init
            self.index = self.entry.index
        self.enabled = self.is_enabled()

    def _should_omit_parsing(self, xml_node):
        return False

    def is_enabled(self):
        if self.entry is None:
            self.enabled = False
        elif self.enabled_formula:
            self.enabled = super().is_enabled()
        else:
            self.enabled = self.entry.is_enabled()
        return self.enabled

    def find_table_entry(self, table, raise_if_not_found=True):
        try:
            for entry in table.children:
                result = entry.calculate_value(self.key_query, allow_calculate=True)
                if not isinstance(result, bool):
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
        return None
