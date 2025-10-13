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

import struct
import operator
from functools import reduce
from enum import Enum

from .IFunction import IFunction
from ...utils import check_value_in_enum
from ...LibException import ComponentException


class ChecksumFunction(IFunction):
    # pylint: disable=line-too-long
    """Calculates checksum value using given operation used to check if the data was not corrupted.

    Checksum function children:

    Configurable children      Required      Description
    ---------------------      --------      -----------
    operation                  yes           Indicates the operation used for checksum calculation, possible are "sum" and "xor"
    """
    # pylint: enable=line-too-long

    operationTag = "operation"

    class Operation(Enum):
        SUM = 'sum'
        XOR = 'xor'

    operation = Operation.SUM

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)

        operation_node = xml_node.find(self.operationTag)
        if operation_node is not None:
            if self.Tags.VALUE not in operation_node.attrib:
                raise ComponentException(f"'{self.operationTag}' tag requires '{self.Tags.VALUE}' attribute", self.name)
            operation_name = operation_node.attrib[self.Tags.VALUE]
            check_value_in_enum(operation_name, self.Operation)
            self.operation = self.Operation(operation_name)

    def _build_layout(self):
        if not self.size:
            self.size = 1
        self.set_value(self.get_default_value())

    def _build(self, buffer):
        super()._build(buffer)
        data = self.get_input_bytes()
        self.set_value(struct.pack("<i", self.calculate_checksum(data))[0:self.size])

    def calculate_checksum(self, data):
        if self.operation == self.Operation.SUM:
            return -sum(data)
        if self.operation == self.Operation.XOR:
            return reduce(operator.xor, data)
        raise ComponentException(f"Undefined checksum operation '{self.operation}' in {self.path}.")
