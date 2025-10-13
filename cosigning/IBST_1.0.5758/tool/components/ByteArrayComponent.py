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
from typing import List

from .IComponent import IComponent
from ..Converter import Converter
from ..LibException import ComponentException
from ..PropertyState import ComponentPreChangeState


class ByteArrayComponent(IComponent):
    """Represents an array of bytes, used to contain or define bigger structures like files.
    It can be used without defining size if it's referencing other byte-like object like different byte-array
    or file data from 'settings'/'configuration' section.
    Byte arrays can be nested in order to build more specific structures.
    Here's an example of byte array:

    ```xml
    <byte_array name="module" >
        <byte_array name="module_length" size="4" calculate="parent.size" />
        <byte_array name="module_data" calculate="/settings/some_file.data" />
        <byte_array name="reserved" size="32" value="0" />
    </byte_array>
    ```
    """

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        value = xml_node.get(IComponent.Tags.VALUE)
        self.empty = value is not None and not value

    def get_parsed_string_value(self, value):
        if self.size is None:
            raise ComponentException('Byte array component requires size attribute to be defined', self.name)
        try:
            value_bytes = Converter.string_to_bytes(value)
            if self.is_setting() and not value_bytes:
                return value_bytes

            value_bytes = self._align_bytes_to_size(value_bytes)

            return value_bytes

        except ValueError as e:
            raise ComponentException(e.args[0], self.name) from None

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        self.empty = not value

        return super().parse_string_value(value)

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

    @property
    def max_str_input_length(self):
        if self.size:
            return self.size * 2
        return None

    def _build_layout(self):
        super()._build_layout()

        if self.value is None and self.value_formula is None and not self.children and self.size is None:
            self.size = 0
            self.set_value(self.get_default_value())

    def set_value(self, value):
        if isinstance(value, int):
            if self.size is None:
                raise ComponentException(
                    f"Size of the '{self.name}' must be known to convert 'number' value to 'byte_array' value",
                    self.name)
            super().set_value(value.to_bytes(self.size, 'little'))
        else:
            super().set_value(value)

    def get_val_string(self, val):
        if val:
            return Converter.bytes_to_string(val)
        return ''

    def _is_empty(self):
        return self.empty

    @property
    def display_user_set_value(self):
        return True

    def _user_xml_value(self):
        """Returns value used in user xml"""
        value = self.user_set_value
        if not value:
            value = self.get_value_string()
        return value
