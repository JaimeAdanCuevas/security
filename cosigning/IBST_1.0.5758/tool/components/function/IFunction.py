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

from ..ByteArrayComponent import ByteArrayComponent
from ...LibException import ComponentException, LibException
from ...structures import DataNode


class IFunction(ByteArrayComponent):
    class Tags(ByteArrayComponent.Tags):
        INPUT = "input"
        DATA = "data"
        SHA = 'sha'

    input_data = []
    input_bytes = None
    decrypted = False

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.align_byte = self.AlignByte.Byte00

    def validate(self):
        pass

    def get_parsed_string_value(self, value):  # pragma: no cover, empty method only for overriding parent one
        pass

    def _parse_children(self, xml_node, **kwargs):
        input_node = xml_node.find(self.Tags.INPUT)

        if input_node is not None:
            self.input_data = self.parse_input_nodes(input_node)

    def parse_input_nodes(self, input_node):
        input_data = []
        for data_node in input_node.findall(self.Tags.DATA):
            try:
                input_data.append(DataNode(data_node))
            except LibException as e:
                raise ComponentException(f"Failed to process input data: {str(e)}", self.name) from None
        return input_data

    def parse_extra_node(self, xml_node, tag_name, value_tag=ByteArrayComponent.Tags.CALCULATE):
        node = xml_node.find(tag_name)
        if node is not None:
            if value_tag not in node.attrib:
                raise ComponentException(f"'{tag_name}' node is missing '{value_tag}' attribute", self.name)
            return node.attrib[value_tag]
        return None

    def _build(self, buffer):
        self.get_input_bytes(buffer, build_process=True)

    def calculate_input_bytes(self, buffer, input_data, build_process=False):
        """This method calculates the value of input data.

        :param buffer: the buffer as reference input data has been given in <path> node with exclude ranges.
        :param input_data: the array of DataNode instances with inputs from input node in <function_hash>.
        :param build_process: boolean flag whether the call is on build-time
                              to set flag that the component has been used in building.
        :return: the calculated data as array of bytes: input bytes from data node or raw data if from path node"""
        input_bytes = bytearray()
        raw_data = bytearray()
        for input_datum in input_data:
            if input_datum.value:
                value = self.calculate_value(formula=input_datum.value, build_process=build_process)
                if not isinstance(value, bytes) and not isinstance(value, bytearray):
                    raise ComponentException(
                        f"Formula '{input_datum.value}' must return 'bytes' or 'bytearray', but returned "
                        f"'{type(value).__name__}'", self.name)
                if input_datum.exclude_ranges:
                    value = self._mask_with_exclude_ranges(value, input_datum.exclude_ranges)
                if input_datum.start_index and input_datum.end_index:
                    start = self.calculate_value(formula=input_datum.start_index)
                    end = self.calculate_value(formula=input_datum.end_index)
                    self._validate_data_offsets_are_in_range(value, start, end)
                    value = value[start:end]
                input_bytes.extend(value)
            elif buffer is None:
                raise ComponentException(f"Buffer was not given - '{self.Tags.DATA}' in '{self.Tags.INPUT}' must use "
                                         f"'{self.Tags.VALUE}' attribute", self.name)
            elif input_datum.path:
                input_component = self.calculate_value(formula=input_datum.path)
                if input_component.offset is not None:
                    input_component.build(buffer)
                input_component_bytes = input_component.get_bytes()
                if input_datum.exclude_ranges:
                    input_component_bytes = self._mask_with_exclude_ranges(input_component_bytes,
                                                                           input_datum.exclude_ranges)
                input_bytes.extend(input_component_bytes)
                if input_component.raw_data:
                    component_raw_data = input_component.raw_data
                    if input_datum.exclude_ranges:
                        component_raw_data = self._mask_with_exclude_ranges(component_raw_data,
                                                                            input_datum.exclude_ranges)
                    raw_data.extend(component_raw_data)
            else:
                start = self.calculate_value(formula=input_datum.start)
                end = self.calculate_value(formula=input_datum.end)
                buffer.seek(start)
                val = buffer.read(end - start)
                if input_datum.exclude_ranges:
                    val = self._mask_with_exclude_ranges(val, input_datum.exclude_ranges)
                input_bytes.extend(val)
                raw_data.extend(val)
        return input_bytes, raw_data

    def _validate_data_offsets_are_in_range(self, input_data, start, end):
        if start >= end:
            raise ComponentException(f"Start offset ({start}) cannot be greater than or equal to end offset ({end}).",
                                     self.name)
        data_length = len(input_data)
        if end > data_length:
            raise ComponentException(f"End offset ({end}) cannot be greater than data length ({data_length}).",
                                     self.name)

    def _mask_with_exclude_ranges(self, val, exclude_ranges_formula: [int, int]):
        exclude_ranges = self.calculate_value(formula=exclude_ranges_formula)
        IFunction.check_if_ranges_are_exclusive(exclude_ranges)
        val = bytearray(val)
        for start, end in exclude_ranges:
            if start > end:
                raise ComponentException(f'Exclude range limit cannot be smaller than its base. '
                                         f'Exclude base: "{start}", '
                                         f'exclude limit: "{end}"')
            if end > len(val):
                raise ComponentException(f'Exclude range limit cannot exceed data size. '
                                         f'Exclude limit: "{end}", '
                                         f'data size: "{len(val)}"')
            val[start:end] = [0xFF] * (end - start)
        return val

    @staticmethod
    def check_if_ranges_are_exclusive(range_tuples: []):
        if len(range_tuples) < 2:
            return
        sorted_ranges = sorted(range_tuples)
        lower_start, lower_end = sorted_ranges.pop()
        while len(sorted_ranges):
            higher_start, higher_end = lower_start, lower_end
            lower_start, lower_end = sorted_ranges .pop()
            if lower_end > higher_start:
                raise ComponentException(f"Exclude ranges are overlapping! {higher_start}:{higher_end} overlaps "
                                         f"{lower_start}:{lower_end}")

    def get_input_bytes(self, buffer=None, build_process=False):
        """This method gets the value of input data.

        :param buffer: the buffer as input for calculate_input_bytes if input data comes from path node.
        :param build_process: boolean flag whether the call is on build-time
                              to set flag that the component has been used in building.
        :return: calculated input bytes."""
        if self.input_bytes is None or self.raw_data is None:
            self.input_bytes, self.raw_data = self.calculate_input_bytes(buffer, self.input_data,
                                                                         build_process=build_process)
        if self.decrypted and self.raw_data:
            return self.raw_data
        return self.input_bytes
