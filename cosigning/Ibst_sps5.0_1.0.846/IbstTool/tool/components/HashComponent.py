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

from .IComponent import IComponent
from ..Converter import Converter
from ..LibException import ComponentException


class HashComponent(IComponent):
    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        if self.buffer is not None:
            self.value = Converter.bytes_to_string(self.value)

        if self.size:
            self.params.gen_value_len(self.size)

    def _parse_string_value(self, value):
        if self.size and (2 * self.size) < len(value):
            raise ComponentException("Value length exceeds the defined limit: " + str(self.size), self.name)

        return value

    def _get_bytes(self):
        return bytes.fromhex(self.value)

    def get_default_value(self):
        return ""

