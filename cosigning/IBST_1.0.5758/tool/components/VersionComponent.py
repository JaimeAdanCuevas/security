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

from .IComponent import IComponent
from ..AttributeGroup import ReadOnlyUiParams
from ..LibException import ComponentException


class VersionComponent(IComponent):
    """Represents a version in string format: x.x.x.x where x is an integer equal or smaller than 65635."""

    VER_SEPARATOR = '.'

    ui_params_class = ReadOnlyUiParams

    @staticmethod
    def string_value_converter(val):
        ex = ComponentException(f"Invalid value for this type: '{str(type(val))}', should be string in version format "
                                f"no longer than x.x.x.x and single version can't be greater than 65 535")

        try:
            version = [int(x) for x in val.split(VersionComponent.VER_SEPARATOR)]
        except ValueError as e:
            raise ex from e

        if len(version) > 4 or any(x > 0xFFFF for x in version):
            raise ex

        if len(version) < 4:
            version += [0] * (4 - len(version))
        return struct.unpack("<Q", (struct.pack("<4H", version[0], version[1], version[2], version[3])))[0]

    def validate(self):
        super().validate()
        if self.value is not None and self.children:
            raise ComponentException("Object with defined value shouldn't have any children", self.name)

        if self.value is None and self.value_formula is None and self.dependency_formula is None and not self.children \
                and not self.is_decomposition_node:
            raise ComponentException("Object has no value and no children", self.name)

    def get_val_string(self, val):
        if val is None:
            return None
        bytes_value = val.to_bytes(8, 'little')
        ver_parts = [str(val) for val in struct.unpack("4H", bytes_value)]
        return VersionComponent.VER_SEPARATOR.join(ver_parts)
