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
from ..LibException import ValueException, ComponentException
from ..Converter import Converter
from ..utils import to_hex
from .IComponentParams import ComponentParams


class NumberComponent(IComponent):

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.byte_order = self.littleOrder
        if self.params:
            self.params.gen_value_min_max(self.size)
        if self.buffer is not None:
            try:
                self.value = int.from_bytes(self.value, self.littleOrder)
            except TypeError:
                raise ComponentException("Cannot convert '{}' value to int", self.value)

    def validate(self):
        super().validate()
        if self.value is not None and self.children:
            raise ComponentException("Object with defined value shouldn't have any children",
                                     self.name)

        if self.value is None and self.value_formula is None and self.dependency_formula is None and not self.children:
            raise ComponentException("Object has no value and no children", self.name)

    def _parse_string_value(self, value):
        if not value:
            raise ComponentException("Value cannot be empty", self.name)

        parsed_val = Converter.string_to_int(value)
        if parsed_val < 0:
            raise ValueException("Cannot set a negative value for a setting", parsed_val, self.name)

        if self.params:
            if self.params.is_min_max_set():
                value_min = self.params.value_int(ComponentParams.ParamsAttr.ValueMin)
                value_max = self.params.value_int(ComponentParams.ParamsAttr.ValueMax)
                if value_min and parsed_val < value_min:
                    raise ValueException("Value cannot be lower than the specified limit: " + hex(value_min), value, self.name)
                if value_max and parsed_val > value_max:
                    raise ValueException("Value cannot be higher than the specified limit: " + hex(value_max), value, self.name)
            if self.params.is_value_list():
                if not self.params.is_in_value_list(parsed_val):
                    raise ValueException("Specified value is not correct. Check this setting params definition for more info", value, self.name)

        return parsed_val

    def _build_layout(self):
        if self.size is None:
            raise ComponentException("Size is not defined", self.name)

        super()._build_layout()

    def _get_bytes(self):
        if not isinstance(self.value, int):
            raise ComponentException("Invalid value for this type: '{}', should be int"
                                     .format(str(type(self.value))), self.name)
        if self.data_size is None:
            raise ComponentException("Size is not defined but is required", self.name)
        return self.value.to_bytes(self.data_size, self.bigOrder)

    def _set_value(self, value):
        if isinstance(value, bytes):
            super()._set_value(int.from_bytes(value, self.byte_order))
        else:
            super()._set_value(value)

    def add_map_entry(self, file, indent):
        off = 0
        value = "null"
        if self.value:
            value = hex(self.value)
        if self.offset and self.offset != -1:
            off = self.offset
        file.write("   " * indent + "%s value: %s\n" % (self.name, value) +
                   "   " * indent + '  ' + " offset: %s size: %s enabled: %s\n" %
                   (hex(off), self.size, self.enabled))

    def get_value_string(self):
        return to_hex(self.value, self.size)
