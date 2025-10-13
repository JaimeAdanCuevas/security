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
from ..LibException import ComponentException


class StringComponent(IComponent):

    def __init__(self, xml_node, **kwargs):
        self.align_byte = self.AlignByte.Byte00
        super().__init__(xml_node, **kwargs)
        self.decomp_dependency = []
        if self.buffer is not None:
            try:
                self.value = self.value.decode("ascii")
            except UnicodeDecodeError:
                raise ComponentException(f"Failed to decode value for '{self.name}'", self.name)
            self.size = len(self.value)
            self.value = self.value.strip('\0')  # string might be padded with zeros
            if self.buffer:
                self.check_validate_formula()
        if self.value is not None and self.size is None:
            self.size = len(self.value)

        if self.size:
            self.params.gen_value_len(self.size)

    def _parse_string_value(self, value):
        import copy
        old_value = copy.copy(self.value)
        self._set_value(value)

        if old_value != value and self.decomp_dependency:
            self._update_decomp_dependency()
        return self.value

    def validate(self):
        super().validate()

        if self.value is not None and self.children:
            raise ComponentException("Object with defined value shouldn't have any children",
                                     self.name)

        if self.value is None and self.value_formula is None and self.dependency_formula is None and not self.children:
            raise ComponentException("Object has no value and no children", self.name)

    def _get_bytes(self):
        return self.value.encode("ascii")

    def get_default_value(self):
        return ""

    def _get_val_string(self, val):
        return val

    def _is_empty(self):
        return not self.value

    def _set_value(self, value):
        if isinstance(value, bytes):
            try:
                string_value = value.decode("ascii")
            except UnicodeDecodeError:
                raise ComponentException(f"Failed to decode value for '{self.name}'", self.name)
            super()._set_value(string_value.strip('\0'))
        else:
            super()._set_value(value)
