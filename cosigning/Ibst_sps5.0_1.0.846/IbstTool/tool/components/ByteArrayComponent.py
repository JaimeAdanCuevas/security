#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2020 Intel Corporation.
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


class ByteArrayComponent(IComponent):

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        value = xml_node.get(IComponent.valueTag)
        self.empty = value is not None and not value

    def _parse_string_value(self, value):
        if self.size is None:
            raise ComponentException('Byte array component requires size attribute to be defined', self.name)

        try:
            self.empty = not value
            value_bytes = Converter.string_to_bytes(value)
            value_bytes = self._align_bytes_to_size(value_bytes)
            return value_bytes

        except ValueError as e:
            raise ComponentException(e.args[0], self.name)

    def validate(self):
        super().validate()

        if self.value is not None and self.size is None:
            raise ComponentException("Value is defined but size not", self.name)

        if self.value is not None and self.children and self.buffer is None:
            raise ComponentException("Object with defined value shouldn't have any children",
                                     self.name)

    def _get_bytes(self):
        return self.value

    def get_default_value(self):
        return self.align_byte * self.size

    def _build_layout(self):
        super()._build_layout()

        if self.value is None and self.value_formula is None and not self.children and self.size is None:
            self.size = 0
            self._set_value(self.get_default_value())

    def _set_value(self, value):
        if isinstance(value, int):
            if self.size is None:
                raise ComponentException(
                    "Size of the '{}' must be known to convert 'number' value to 'byte_array' value".format(self.name),
                    self.name)
            super()._set_value(value.to_bytes(self.size, 'little'))
        else:
            super()._set_value(value)

    def _get_val_string(self, val):
        if val:
            return Converter.bytes_to_string(val)
        return ''

    def _is_empty(self):
        return self.empty
