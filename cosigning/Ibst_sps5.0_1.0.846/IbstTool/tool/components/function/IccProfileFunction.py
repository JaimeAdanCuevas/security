#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2019-2020 Intel Corporation.
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


class IccProfileFunction(IFunction):

    registerListTag = "registersList"
    registerNodePath = None
    registerNodeComponent = None
    FLAGS_BUNDLE_SIZE = 8
    ENDPOINT_REGISTER_SIZE = 8
    REGISTER_SIZE = 4

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        if self.registerListTag not in xml_node.attrib:
            raise ComponentException(f"{self.registerListTag} missing in {self.name} function.")
        self.registerNodePath = xml_node.attrib[self.registerListTag]

    def _build_layout(self):
        self.registerNodeComponent = self.calculate_value_from_path(self.registerNodePath)
        self.size = self.FLAGS_BUNDLE_SIZE
        for child in self.registerNodeComponent.children:
            if child.value_formula is not None:
                child.value = child.calculate_value(child.value_formula, allow_calculate=True)
            if not child.is_default():
                self.size += self.ENDPOINT_REGISTER_SIZE
        self._set_value(self.get_default_value())

    def _build(self, buffer):
        all_registers_list = self.registerNodeComponent.children
        non_default_registers_list = []
        for index in range(1, len(all_registers_list), 2):
            if not all_registers_list[index].is_default():
                non_default_registers_list.append(all_registers_list[index - 1])
                non_default_registers_list.append(all_registers_list[index])
        non_default_registers_count = len(non_default_registers_list)
        flags = 0x00010000 + self.FLAGS_BUNDLE_SIZE + non_default_registers_count*self.REGISTER_SIZE
        self.value = flags.to_bytes(self.REGISTER_SIZE, self.littleOrder)
        self.value += (non_default_registers_count//2).to_bytes(self.REGISTER_SIZE, self.littleOrder)
        for entry in non_default_registers_list:
            self.value += entry.value.to_bytes(self.REGISTER_SIZE, self.littleOrder)
