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

import struct
import operator
from functools import reduce
from enum import Enum

from .IFunction import IFunction
from ...utils import check_value_in_enum
from ...LibException import ComponentException


class ChecksumFunction(IFunction):

    operationTag = "operation"

    class Operation(Enum):
        sum = 'sum'
        xor = 'xor'

    operation = Operation.sum

    def parse_children(self, xml_node, buffer=None):
        super().parse_children(xml_node)

        operation_node = xml_node.find(self.operationTag)
        if operation_node is not None:
            if self.valueTag not in operation_node.attrib:
                raise ComponentException("'{}' tag requires '{}' attribute"
                                         .format(self.operationTag, self.valueTag), self.name)
            operation_name = operation_node.attrib[self.valueTag]
            check_value_in_enum(operation_name, self.Operation)
            self.operation = self.Operation(operation_name)

    def _build_layout(self):
        if not self.size:
            self.set_size(1)
        self._set_value(self.get_default_value())

    def _build(self, buffer):
        super()._build(buffer)
        data = self.get_input_bytes()
        self._set_value(struct.pack("<i", self.calculate_checksum(data))[0:self.size])

    def calculate_checksum(self, data):
        if self.operation == self.Operation.sum:
            return -sum(data)
        if self.operation == self.Operation.xor:
            return reduce(operator.xor, data)
