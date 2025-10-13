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


from .IFunction import IFunction
from ...LibException import ComponentException


class UpdateValueFunction(IFunction):
    nodeTag = "node"
    newValueTag = "new_value"

    node_path = None
    new_value_path = None
    new_value = None

    def build(self, buffer):
        if not self._is_enabled():
            return

        node_to_update = self.calculate_value_from_path(self.node_path)
        cur_offset = buffer.tell()
        if self.new_value:
            node_to_update.parse_string_value(self.new_value)
        if self.new_value_path:
            new_value = self.calculate_value(self.new_value_path, allow_calculate=True)
            node_to_update._set_value(new_value)
        node_to_update._write_bytes(node_to_update.get_bytes(), buffer, node_to_update.offset)
        buffer.seek(cur_offset)

    def parse_children(self, xml_node, buffer=None):
        node = self._parse_node(xml_node, self.nodeTag)
        new_value = self._parse_node(xml_node, self.newValueTag)
        self.node_path = self._parse_attribute(node, self.calculateTag)
        self.new_value_path = None
        self.new_value = None

        if self.calculateTag in new_value.attrib:
            self.new_value_path = new_value.attrib[self.calculateTag]

        if self.valueTag in new_value.attrib:
            self.new_value = new_value.attrib[self.valueTag]

        if self.new_value is None and self.new_value_path is None:
            raise ComponentException("Could not find required attributes for '%s': %s or %s" %
                                     (self.newValueTag, self.calculateTag, self.valueTag), self.name)

    def _build_layout(self):
        pass
