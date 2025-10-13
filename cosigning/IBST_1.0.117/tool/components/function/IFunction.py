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

from ..ByteArrayComponent import ByteArrayComponent
from ...LibException import ComponentException, LibException
from ...structures import DataNode


class IFunction(ByteArrayComponent):
    inputTag = "input"
    dataTag = "data"

    input_data = None
    input_bytes = None
    decrypted = False

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.align_byte = self.AlignByte.Byte00

    def validate(self):
        pass

    def _parse_string_value(self, value):
        pass  # pragma: no cover

    def parse_children(self, xml_node, buffer = None):
        self.parse_input_nodes(xml_node)

    def parse_input_nodes(self, xml_node):
        input_node = xml_node.find(self.inputTag)

        if input_node is not None:
            self.input_data = []
            for data_node in input_node.findall(self.dataTag):
                try:
                    self.input_data.append(DataNode(data_node))
                except LibException as e:
                    raise ComponentException("Failed to process input data: {}".format(e.args[0]),
                                             self.name)

    def parse_extra_node(self, xml_node, tag_name):
        node = xml_node.find(tag_name)
        if node is not None:
            if self.calculateTag not in node.attrib:
                raise ComponentException("'{}' node is missing '{}' attribute".
                                         format(tag_name, self.calculateTag),
                                         self.name)
            return node.attrib[self.calculateTag]

    def _build(self, buffer):
        self.calculate_input_bytes(buffer)

    def calculate_input_bytes(self, buffer):
        self.input_bytes = bytearray()
        self.raw_data = bytearray()
        for input_datum in self.input_data:
            if input_datum.value:
                value = self.calculate_value(formula=input_datum.value)
                if not isinstance(value, bytes) and not isinstance(value, bytearray):
                    raise ComponentException("Formula '{}' must return 'bytes' or 'bytearray', but returned '{}'"
                                             .format(input_datum.value, type(value).__name__), self.name)
                self.input_bytes.extend(value)
            elif input_datum.path:
                input_component = self.calculate_value(formula=input_datum.path)
                if input_component.offset is not None:
                    input_component.build(buffer)
                self.input_bytes.extend(input_component.get_bytes())
                if input_component.raw_data:
                    self.raw_data.extend(input_component.raw_data)
            else:
                start = self.calculate_value(formula=input_datum.start)
                end = self.calculate_value(formula=input_datum.end)
                buffer.seek(start)
                val = buffer.read(end - start)
                self.input_bytes.extend(val)
                self.raw_data.extend(val)

    def get_input_bytes(self):
        if self.decrypted and self.raw_data:
            return self.raw_data
        return self.input_bytes
