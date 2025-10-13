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
from enum import Enum
from typing import List

from ..FileManager import FileManager
from ..FileOpener import open_file
from .ByteArrayComponent import ByteArrayComponent
from ..LibConfig import LibConfig
from ..LibException import ComponentException, LibException, FileException, InvalidFilePathException
from ..Converter import Converter
from ..PropertyState import ComponentPreChangeState
from ..structures import DataNode
from ..utils import MapData, check_for_illegal_characters


class FileComponent(ByteArrayComponent):
    """Represents a file read in bytes, value should be a string with path to the file.
    The path is validated and the size can also be validated if the size attribute is given.
    Smaller data pieces can also be acquired and used later by decomposing the file.

    ```xml
    <file name="file_to_hash" value="default_path/file.bin" >
        <decompose>
          <data name="some_part" start="0x24" end="0xE1" />
          <data name="some_other_part" start="0x80" end="0x0" />
        </decompose>
    </file>
    ```

    (end=0x0 means the entire file length)

    File component special properties

    Special property    Description
    ----------------    -----------
    data                Acquires file data, can be used with a range e.g. data[4:16], data[0xA:0xC2E], data[128:]
    path                Gets file path
    """

    class Tags(ByteArrayComponent.Tags):
        DECOMPOSE = "decompose"
        DATA = "data"
        REQUIRED = "required"
        END = "end"
        OUTPUT_FILE = "output_file"

    class ComponentProperty(Enum):
        SIZE = "size"
        DATA = "data"
        ANY = "any"
        PATH = "path"
        EMPTY = "empty"
        MAP_NAME = ByteArrayComponent.ComponentProperty.MAP_NAME.value
        LEGACY_MAP_NAME = ByteArrayComponent.ComponentProperty.LEGACY_MAP_NAME.value
        OFFSET = ByteArrayComponent.ComponentProperty.OFFSET.value

    decomp_data = {}
    data_offset = None
    file_offset = None
    required_formula = None
    _data = None
    expected_size = None
    output_file = False

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.default_value = self.value
        self.decomp_dependency = []

    @property
    def data(self):
        if self._data is None:  # lazy fetching
            self._load_data()
            if self.size is None:
                raise ComponentException(f"Cannot calculate size for '{self.name}'")
            if not self.output_file:
                self._data = self._data[self.file_offset:self.file_offset + self.size]
        return self._data

    @property
    def required(self):
        return self.calculate_value(self.required_formula)

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        self._data = None
        self.file_offset = 0
        self.size = 0

        return super().parse_string_value(value)

    def get_parsed_string_value(self, value):
        if value and self.name == 'output_file' and os.path.splitext(value)[1] != '.bin':
            raise ComponentException(f"Output file '{value}' extension must be: *.bin", self.name)
        check_for_illegal_characters(value)

        if self.value != value and value and self.decomp_dependency:
            self._update_decomp_dependency()
        value = FileManager.remove_whitespace_from_output_file(value)

        return value

    def _parse_children(self, xml_node, **kwargs):
        try:
            self._parse_start_offset(xml_node)
            self._parse_end_offset(xml_node)
            self._parse_decompose(xml_node)
        except ComponentException as ex:
            self.error_message = str(ex)

    def clear(self):
        self.file_offset = 0
        self._data = bytes()

    def _load_data(self):
        if self.value_formula:
            self.value = self.calculate_value(self.value_formula)
        if not self.value and not self.required:
            self.clear()
            return

        self._validate_file()
        if not self.output_file:
            self.clear()
            with open_file(self.value, "rb") as f:
                self._data = f.read()
                if not self.size or self.value_formula:
                    self.size = len(self._data)
                if self.size_formula:
                    self.size = self.calculate_value(self.size_formula)
                    if len(self._data) != self.size:
                        raise ComponentException(f"Invalid size of external_data, should be {self.size} but is "
                                                 f"{len(self._data)}", self.name)

    def set_data(self, data: bytes):
        self._data = data
        self.size = len(data)

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self.expected_size = self._parse_attribute(xml_node, self.Tags.SIZE, False)
        if self.expected_size:
            self.expected_size = Converter.string_to_int(self.expected_size)
        self.required_formula = self._parse_attribute(xml_node, self.Tags.REQUIRED, required=False, default="True")
        self.output_file = Converter.string_to_bool(
            self._parse_attribute(xml_node, self.Tags.OUTPUT_FILE, required=False, default="False"))

    def _parse_start_offset(self, xml_node):
        offset_node = xml_node.find(self.Tags.OFFSET)
        if offset_node is not None:
            if self.Tags.VALUE not in offset_node.attrib:
                raise ComponentException(f"'{self.Tags.OFFSET}' tag is missing mandatory '{self.Tags.VALUE}' "
                                         f"attribute", self.name)
            if not offset_node.attrib[self.Tags.VALUE]:
                raise ComponentException(f"'{self.Tags.OFFSET}' tag has empty '{self.Tags.VALUE}' attribute", self.name)
            self.file_offset = Converter.string_to_int(offset_node.attrib[self.Tags.VALUE])

    def _parse_end_offset(self, xml_node):
        end_node = xml_node.find(self.Tags.END)
        if end_node is not None:
            if self.Tags.VALUE not in end_node.attrib:
                raise ComponentException(f"'{self.Tags.END}' tag is missing mandatory '{self.Tags.VALUE}' attribute",
                                         self.name)
            if not end_node.attrib[self.Tags.VALUE]:
                raise ComponentException(f"'{self.Tags.END}' tag has empty '{self.Tags.VALUE}' attribute", self.name)
            end_offset = Converter.string_to_int(end_node.attrib[self.Tags.VALUE])
            if self.file_offset:
                if self.file_offset > end_offset:
                    raise ComponentException(f"'{self.Tags.OFFSET}' value: '{self.file_offset}' cannot be larger "
                                             f"than '{self.Tags.END}' value: {end_offset}'", self.name)
                self.size = end_offset - self.file_offset
            else:
                self.size = end_offset

    def _parse_decompose(self, xml_node):
        decompose_node = xml_node.find(self.Tags.DECOMPOSE)

        if decompose_node is None:
            return

        for data_node in decompose_node.findall(self.Tags.DATA):
            try:
                data = DataNode(data_node)
                data.check_start_end()
                data.check_name()
                self.decomp_data[data.name] = data
            except LibException as e:
                raise ComponentException(f"Failed to process input data: {e.args[0]}", self.name) from None

    def _get_property(self, component_property, _=False, report_usage=False):
        if report_usage:
            self.set_data_used_for_building(report_usage)
        if component_property == self.ComponentProperty.SIZE:
            if not self._data:  # lazy fetching, we have to load data, to have its size
                _ = self.data
            return self.size
        if component_property == self.ComponentProperty.DATA:
            return self.data
        if component_property == self.ComponentProperty.ANY:
            if component_property.value in self.decomp_data:
                data_range = self.decomp_data[component_property.value]
                start = Converter.string_to_int(data_range.start)
                end = Converter.string_to_int(data_range.end)
                if end == 0:
                    end = len(self.data)
                return self.data[start:end]
            raise ComponentException(f"{component_property.value} could not be found!", self.name)
        if component_property == self.ComponentProperty.PATH:
            return self.value
        if component_property == self.ComponentProperty.EMPTY:
            return not bool(self.value)
        if component_property == self.ComponentProperty.MAP_NAME:
            if "/" in self.map_name:
                try:
                    calculated_val = self.calculate_value(formula=self.map_name, allow_calculate=_)
                    return calculated_val
                except ComponentException:
                    return self.map_name
            else:
                return self.map_name
        if component_property == self.ComponentProperty.LEGACY_MAP_NAME:
            if LibConfig.pathSeparator in self.legacy_map_name:
                try:
                    return self.calculate_value(formula=self.legacy_map_name, allow_calculate=_)
                except ComponentException:
                    return self.legacy_map_name
            else:
                return self.legacy_map_name
        if component_property == self.ComponentProperty.OFFSET:
            return self.offset
        return None

    def _get_component_property(self, property_name):
        if property_name not in (prop.value for prop in self.ComponentProperty):
            enum_dic = {m.name: m.value for m in self.ComponentProperty}
            enum_dic[self.ComponentProperty.ANY.name] = property_name
            self.ComponentProperty = Enum('ComponentProperty', enum_dic)  # pylint: disable=invalid-name
        return super()._get_component_property(property_name)

    def _get_bytes(self):
        return self.data

    def get_val_string(self, val):
        return val

    def _copy_to(self, dst):
        super()._copy_to(dst)
        # pylint: disable=protected-access
        dst.required_formula = self.required_formula
        dst.file_offset = self.file_offset
        dst.decomp_data = self.decomp_data
        dst.expected_size = self.expected_size
        dst._data_used_for_building = self._data_used_for_building
        # pylint: enable=protected-access

    def validate_file_size(self):
        if self.expected_size and self.value:

            if not os.path.exists(self.value):
                raise ComponentException(f"File '{self.value}' does not exist")

            real_file_size = os.path.getsize(self.value)
            if self.expected_size != real_file_size:
                file_name = os.path.basename(self.value)
                raise ComponentException(f"File {file_name} size for {self.name} is not equal to expected size. "
                                         f"Expected size is {self.expected_size}.")

    def _clear_data(self):
        self.file_offset = 0
        self.size = 0
        self._data = None

    def validate_during_overriding(self):
        self._validate_file()

    def _validate_file(self):
        try:
            FileManager.validate_path(self.value, for_saving=self.output_file)
        except FileException as ex:
            raise ComponentException(str(ex), self.display_name) from None
        self.validate_file_size()

    @property
    def display_user_set_value(self):
        return False

    @property
    def map_data(self) -> [MapData]:
        """Returns list of start offset, length, intent, area name"""
        data = super().map_data
        if self.value_formula and self.value_formula.startswith('/required_containers/'):
            api_component = self.expr_engine.calculate_component_from_path(self.value_formula)
            if hasattr(api_component, 'children_map_data') and api_component.children_map_data:
                for item in api_component.children_map_data:
                    data.append(MapData(item.offset + self.offset, item.length, item.indent + 1, item.map_name))
        return data
