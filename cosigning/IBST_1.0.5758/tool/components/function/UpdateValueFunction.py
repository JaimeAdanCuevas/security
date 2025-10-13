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
import re
from ...Converter import Converter
from .IFunction import IFunction
from ...LibException import ComponentException


class UpdateValueFunction(IFunction):
    """This function can be used to set different component's value, it can be very useful when some operation
    can be done only after component declaration. Here's a practical example:

    ```xml
    <layout>
        <byte_array name="data_crc" size="4" />
        <byte_array name="entire_data">
            <byte_array name="file_data" calculate="/settings/input_file.data" />
            <byte_array name="reserved" value="0" size="20" />
        </byte_array>
        <function_crc name="data_crc_result" calc_only="True">
            <crc_type value="crc16"/>
            <input>
                <data path="parent/entire_data"/>
            </input>
        </function_crc>
        <function_update_value>
            <node calculate="parent/data_crc"/>
            <new_value calculate="parent/data_crc_result.value"/>
        </function_update_value>
    </layout>
    ```

    Crc value needs to be on top of the binary, but we can calculate it only once the data gets processed,
    that's where function_update_value can be very helpful.

    Update value function configurable children:

    Configurable children   Required    Description
    ---------------------   --------    -----------
    node                    yes         Points to the node (component) which value should be replaced
    new_value               yes         New value for component
    """

    class Tags(IFunction.Tags):
        NODE = "node"
        NEW_VALUE = "new_value"

    node_path = None
    new_value_path = None
    new_value = None

    def build(self, buffer):
        if not self.is_enabled():
            return

        node_to_update = self.calculate_value_from_path(self.node_path)
        cur_offset = buffer.tell()

        if self.new_value:
            node_to_update.parse_string_value(self.new_value)
            new_value = node_to_update.value
        if self.new_value_path:
            new_value = self.calculate_value(self.new_value_path, allow_calculate=True, build_process=True)
            node_to_update.set_value(new_value)

        node_bytes = self._get_bytes_from_node(node_to_update)
        node_to_update.write_bytes_to_buffer(node_bytes, buffer, node_to_update.offset)
        buffer.seek(cur_offset)

        if node_to_update.parent:
            new_value = Converter.to_bytes(new_value, node_to_update.size, byte_order=node_to_update.byte_order)
            self._set_value_for_parent(node_to_update, node_to_update.parent, new_value)

    @staticmethod
    def _set_value_for_parent(node_to_update, parent, new_value):
        if parent.value and parent.offset is not None:
            offset_delta = node_to_update.offset - parent.offset
            parent_val = parent.value
            parent.value = parent_val[:offset_delta] + new_value + parent_val[offset_delta + node_to_update.size:]

        if parent.parent:
            UpdateValueFunction._set_value_for_parent(node_to_update, parent.parent, new_value)

    def _get_bytes_from_node(self, node):
        try:
            return node.get_bytes()
        except ComponentException as e:
            regex = r"Provided value is too big \(\d* bytes\), maximum size is \d* bytes"
            file_too_large_messages = re.findall(regex, e.message)
            if file_too_large_messages:
                raise ComponentException("\n".join(file_too_large_messages).replace("value", "file"), self.name) \
                    from None
            raise e

    def _parse_children(self, xml_node, **kwargs):
        node = self._parse_node(xml_node, self.Tags.NODE)
        new_value = self._parse_node(xml_node, self.Tags.NEW_VALUE)
        self.node_path = self._parse_attribute(node, self.Tags.CALCULATE)
        self.new_value_path = None
        self.new_value = None

        if self.Tags.CALCULATE in new_value.attrib:
            self.new_value_path = new_value.attrib[self.Tags.CALCULATE]

        if self.Tags.VALUE in new_value.attrib:
            self.new_value = new_value.attrib[self.Tags.VALUE]

        if self.new_value is None and self.new_value_path is None:
            raise ComponentException(f"Could not find required attributes for '{self.Tags.NEW_VALUE}': "
                                     f"{self.Tags.CALCULATE} or {self.Tags.VALUE}", self.name)

    def _build_layout(self):
        pass
