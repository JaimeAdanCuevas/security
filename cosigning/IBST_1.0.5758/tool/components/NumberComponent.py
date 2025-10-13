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

from .IComponent import IComponent
from ..ColorPrint import log
from ..LibException import ValueException, ComponentException, ValidateException
from ..Converter import Converter
from ..utils import to_hex, parse_json_str, get_item_from_structure, XmlAttrType, XmlAttr, get_min_max_values
from .IComponentParams import ComponentParams, DisplayMode


class NumberComponent(IComponent):
    """Represents a number (either in decimal or in hex, starting with 0x)."""

    class Tags(IComponent.Tags):
        BIT_LOW = "bit_low"
        BIT_HIGH = "bit_high"
        DISPLAY_MODE = "display_mode"
        SIGNED = "signed"

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.byte_order = self.littleOrder
        if self.params:
            if self.dependency_formula:
                dependency_dict = parse_json_str(self.dependency_formula)
                bit_low = get_item_from_structure(dependency_dict, self.Tags.BIT_LOW)
                bit_high = get_item_from_structure(dependency_dict, self.Tags.BIT_HIGH)
                if bit_low is not None and bit_high is not None:
                    self.params.gen_value_min_max_from_bits(bit_low, bit_high, self.display_mode)
                else:
                    self.params.gen_value_min_max(self.size, self.signed, self.display_mode)
            else:
                self.params.gen_value_min_max(self.size, self.signed, self.display_mode)
        if self.buffer is not None:
            try:
                self.set_value(int.from_bytes(self.value, self.littleOrder))
            except TypeError as e:
                raise ComponentException(f"Cannot convert '{self.value}' value to int") from e
        self.default_value = self.value

    def validate(self):
        super().validate()
        if self.value is not None and self.children:
            raise ComponentException("Object with defined value shouldn't have any children", self.name)

        has_no_value = self.value is None and self.value_formula is None
        has_no_dependency_formula = self.dependency_formula is None and self.duplicates_formula is None
        if has_no_value and has_no_dependency_formula and not self.children and not self.is_decomposition_node:
            raise ComponentException("Object has no value and no children", self.name)

    def display_func(self, val):
        if val is None:
            return None
        if self.display_mode == DisplayMode.HEX.value and self.signed:
            return to_hex(val, self.size).upper().replace("X", "x")
        if val >= 0 and self.display_mode == DisplayMode.HEX.value:
            return hex(val).upper().replace("X", "x")
        return str(val)

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        signed = XmlAttr(name=self.Tags.SIGNED, is_required=False, default=False, attr_type=XmlAttrType.BOOL,
                         xml_node=xml_node)
        display_mode = XmlAttr(name=self.Tags.DISPLAY_MODE, is_required=False, default=DisplayMode.HEX.value,
                               attr_type=XmlAttrType.STRING, xml_node=xml_node)
        self.signed = signed.value
        self.display_mode = display_mode.value

    def _max_value(self):
        return 2 ** (self.size * 8) - 1

    @property
    def max_str_input_length(self):
        if self.params.is_min_max_set():
            max_val_int = self.params.value_int(ComponentParams.ParamsAttr.VALUE_MAX)
            min_val_int = self.params.value_int(ComponentParams.ParamsAttr.VALUE_MIN)
        elif self.size:
            max_val_int = int(get_min_max_values(self.size, self.signed)[1], 16)
            min_val_int = int(get_min_max_values(self.size, self.signed)[0], 16)
        else:
            return None

        max_val_hex_str = hex(max_val_int)
        max_val_dec_str = str(max_val_int)
        min_val_hex_str = hex(min_val_int)
        min_val_dec_str = str(min_val_int)
        return max(len(max_val_hex_str), len(max_val_dec_str), len(min_val_hex_str), len(min_val_dec_str))

    def get_parsed_string_value(self, value):
        parsed_val = super().get_parsed_string_value(value)

        if not self.signed and parsed_val < 0:
            raise ValueException("Cannot set a negative value for a setting", self.display_func(parsed_val), self.name)

        if self.size is not None and parsed_val > self._max_value():
            max_val = self.display_func(self._max_value())
            value = self.display_func(parsed_val)
            raise ValueException(f"Value cannot be longer than the specified limit: {max_val}", value, self.name)

        return parsed_val

    def _build_layout(self):
        if self.size is None:
            raise ComponentException("Size is not defined", self.name)

        super()._build_layout()

    def _get_bytes(self):
        if not isinstance(self.value, int):
            raise ComponentException(f"Invalid value for this type: '{str(type(self.value))}', should be int",
                                     self.name)
        if self.size is None:
            raise ComponentException("Size is not defined but is required", self.name)
        return self.value.to_bytes(self.size, self.bigOrder, signed=self.signed)

    def set_value(self, value):  # val: "str/int/bytearray/byte"
        int_value = value
        if isinstance(value, (bytes, bytearray)):
            int_value = int.from_bytes(value, self.byte_order)
        if isinstance(value, str):
            int_value = Converter.string_to_int(value)
        try:
            self._validate_min_max(int_value)
            super().set_value(int_value)
        except ValidateException as e:
            if not self.params.skip_value_list_validation or self.component_type == 'Bit' \
                    or (not e.value_list and not e.min_max):
                raise e  # pylint: disable=duplicate-code
            if e.value_list:
                validate_str = f"Possible values: {e.value_list}"
                err_str = "does not match any value from the list"
            elif e.min_max:
                validate_str = f"Limit value: {e.min_max}"
                err_str = "exceeds the limit value"
            log().warning(f"Value '{e.value}' from '{e.object_name}' {err_str} - "
                          f"forcing value from register\n{validate_str}.")
            self.value = int_value

    def _validate_min_max(self, value: int):
        if self.params and self.params.is_min_max_set():
            value_min = self.params.value_int(ComponentParams.ParamsAttr.VALUE_MIN)
            value_max = self.params.value_int(ComponentParams.ParamsAttr.VALUE_MAX)

            if value < value_min:
                raise ValidateException("Value is lower than the specified minimum: " + self.display_func(value_min),
                                        self.display_func(value),
                                        min_max=self.display_func(value_min),
                                        component_name=self.name)
            if value > value_max:
                raise ValidateException("Value is higher than the specified maximum: " + self.display_func(value_max),
                                        self.display_func(value),
                                        min_max=self.display_func(value_max),
                                        component_name=self.name)

    def get_val_string(self, val):
        if isinstance(val, bytes):
            return Converter.bytes_to_hex_string(val)
        if val is not None and val < 0:
            return str(val)
        return to_hex(val, self.size)
