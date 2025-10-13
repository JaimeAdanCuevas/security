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
from .IComponent import IComponent
from ..LibException import ComponentException
from ..Converter import Converter


class VersionComponent(IComponent):
    ver_separator = '.'

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.read_only = True

    def _parse_string_value(self, value):
        try:
            parsed_val = Converter.string_to_int(value, False)
            if parsed_val is not None:
                return parsed_val
        except ValueError:
            pass  # just to silence the exception
        ex = ComponentException("Invalid value for this type: '{}', should be string in version format x.x.x.x"
                                .format(str(type(value))), self.name)
        try:
            version = [int(x) for x in value.split(VersionComponent.ver_separator)]
        except ValueError:
            raise ex

        if len(version) != 4 or any(x > 0xFFFF for x in version):
            raise ex
        return struct.unpack("<Q", (struct.pack("<4H", version[0], version[1], version[2], version[3])))[0]

    def validate(self):
        super().validate()
        if self.value is not None and self.children:
            raise ComponentException("Object with defined value shouldn't have any children",
                                     self.name)

        if self.value is None and self.value_formula is None and self.dependency_formula is None and not self.children:
            raise ComponentException("Object has no value and no children", self.name)

    def get_value_string(self):
        bytes_value = self.value.to_bytes(8, 'little')
        ver_parts = [str(val) for val in struct.unpack("4H", bytes_value)]
        return VersionComponent.ver_separator.join(ver_parts)
