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
from enum import Enum

from .ByteArrayComponent import ByteArrayComponent
from ..LibException import ComponentException, FunctionException, LibException
from ..Converter import Converter
from ..structures import DataNode
from ..utils import validate_file
import os


class FileComponent(ByteArrayComponent):
    offsetTag = "offset"
    sizeTag = "size"
    decomposeTag = "decompose"
    dataTag = "data"
    requiredTag = "required"
    endTag = "end"

    class ComponentProperty(Enum):
        Size = "size"
        Data = "data"
        Any = "any"
        Path = "path"
        Empty = "empty"

    decomp_data = {}
    data_offset = None
    file_offset = None
    required = None
    _data = None
    expected_size = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.decomp_dependency = []

    @property
    def data(self):
        if self._data is None:  # lazy fetching
            self._load_data()
            self._data = self._data[self.file_offset:self.file_offset + self.size]
        return self._data

    def _parse_string_value(self, value):
        self._data = None
        self.file_offset = 0
        self._parse_string_path_value(value)
        self.size = 0
        return self.value

    def parse_children(self, xml_node, buffer=None):
        try:
            self._parse_start_offset(xml_node)
            self._parse_end_offset(xml_node)
            self._parse_decompose(xml_node)
        except ComponentException as ex:
            self.error_message = str(ex)

    def clear(self):
        self.file_offset = 0
        self._data = bytes()

    # TODO: what if calculate refers to 'layout' part???
    def _load_data(self):
        if self.value_formula:
            self.value = self.calculate_value(self.value_formula)
        if not self.value and not self.required:
            self.clear()
            return

        try:
            validate_file(self.value)
        except LibException as ex:
            raise ComponentException(str(ex), self.name)

        self.validate_file_size()

        self.clear()
        with open(self.value, "rb") as f:
            self._data = f.read()
            if not self.size:
                self.size = len(self._data)

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self.expected_size = self._parse_attribute(xml_node, self.sizeTag, False)
        if self.expected_size:
            self.expected_size = Converter.string_to_int(self.expected_size)

    def _parse_start_offset(self, xml_node):
        offset_node = xml_node.find(self.offsetTag)
        if offset_node is not None:
            if self.valueTag not in offset_node.attrib:
                raise ComponentException("'{}' tag is missing mandatory '{}' attribute"
                                         .format(self.offsetTag, self.valueTag), self.name)
            if not offset_node.attrib[self.valueTag]:
                raise ComponentException("'{}' tag has empty '{}' attribute"
                                         .format(self.offsetTag, self.valueTag), self.name)
            self.file_offset = Converter.string_to_int(offset_node.attrib[self.valueTag])

    def _parse_end_offset(self, xml_node):
        end_node = xml_node.find(self.endTag)
        if end_node is not None:
            if self.valueTag not in end_node.attrib:
                raise ComponentException("'{}' tag is missing mandatory '{}' attribute"
                                         .format(self.endTag, self.valueTag), self.name)
            if not end_node.attrib[self.valueTag]:
                raise ComponentException("'{}' tag has empty '{}' attribute"
                                         .format(self.endTag, self.valueTag), self.name)
            end_offset = Converter.string_to_int(end_node.attrib[self.valueTag])
            if self.file_offset:
                if self.file_offset > end_offset:
                    raise ComponentException("'{}' value: '{}' cannot be larger than '{}' value: {}'"
                                             .format(self.offsetTag, self.file_offset, self.endTag, end_offset), self.name)
                self.size = end_offset - self.file_offset
            else:
                self.size = end_offset

    def _parse_decompose(self, xml_node):
        decompose_node = xml_node.find(self.decomposeTag)

        if decompose_node is None:
            return

        for data_node in decompose_node.findall(self.dataTag):
            try:
                data = DataNode(data_node)
                data.check_start_end()
                data.check_name()
                self.decomp_data[data.name] = data
            except (FunctionException, LibException) as e:
                raise ComponentException("Failed to process input data: {}".format(e.args[0]),
                                         self.name)

    def _get_property(self, component_property, _=False):
        if component_property == self.ComponentProperty.Size:
            if not self._data:  # lazy fetching, we have to load data, to have its size
                _ = self.data
            return self.size
        if component_property == self.ComponentProperty.Data:
            return self.data
        if component_property == self.ComponentProperty.Any:
            if component_property.value in self.decomp_data:
                dataRange = self.decomp_data[component_property.value]
                start = Converter.string_to_int(dataRange.start)
                end = Converter.string_to_int(dataRange.end)
                return self.data[start:end]
            raise ComponentException("{} could not be found!"
                                     .format(component_property.value), self.name)
        if component_property == self.ComponentProperty.Path:
            return self.value
        if component_property == self.ComponentProperty.Empty:
            return not bool(self.value)

    def _get_component_property(self, property_name):
        if property_name not in self.ComponentProperty._value2member_map_:
            enumDic = {m.name: m.value for m in self.ComponentProperty}
            enumDic[self.ComponentProperty.Any.name] = property_name
            self.ComponentProperty = Enum('ComponentProperty', enumDic)
        return super()._get_component_property(property_name)

    def _get_bytes(self):
        return self.data

    def _get_val_string(self, val):
        return val

    def _parse_string_path_value(self, value):
        import copy
        old_value = copy.copy(self.value)
        self._set_value(value)

        if old_value != value and self.decomp_dependency:
            self._update_decomp_dependency()

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst.required = self.required
        dst.file_offset = self.file_offset
        dst.decomp_data = self.decomp_data
        dst.expected_size = self.expected_size

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
        self._data = None

