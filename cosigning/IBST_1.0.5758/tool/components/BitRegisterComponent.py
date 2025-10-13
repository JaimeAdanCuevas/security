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

from .BitFieldComponent import BitFieldComponent
from .IComponentParams import DisplayMode
from ..Converter import Converter
from ..ColorPrint import log
from ..LibException import ComponentException
from ..PropertyState import PropertyState, ComponentPreChangeState


class BitRegisterComponent(BitFieldComponent):

    def __init__(self, xml_node, **kwargs):
        self.signed = False
        if self.Tags.VALUE in xml_node.attrib:
            self.default_register_value = Converter.string_to_int(xml_node.attrib[self.Tags.VALUE])
        else:
            self.default_register_value = None
        super().__init__(xml_node, **kwargs)
        if self.default_register_value is not None:
            modified = self._apply_value_to_bits(self.default_register_value)
            if modified:
                for each in (modified_result[0] for modified_result in modified):
                    log().debug(f'{each.name} value was overwritten to {each.get_value_string()} to be consistent '
                                f'with range {each.bit_low}:{each.bit_high} '
                                f'of its parent {each.parent.name} value={each.parent.get_value_string()}')

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        self._generate_missing_children()

    def _generate_missing_children(self):
        missing_bits_array = list(range(0, self.size * 8))
        for bit_param in self.bit_fields:
            for bit in range(bit_param.bit_low, bit_param.bit_high + 1):
                if bit in missing_bits_array:
                    missing_bits_array.remove(bit)
                else:
                    raise ComponentException(f"Bit {bit} is referred by more than one child of BitRegister", self.name)
        if missing_bits_array:
            bit_scopes = self._get_bit_scopes(missing_bits_array)
            for bit_range in bit_scopes:
                bit_low, bit_high = bit_range
                name = f"reserved_{self.name}_{bit_low}-{bit_high}"
                new_bit = BitFieldComponent.Bit.init_without_xml_node(name=name, bit_low=bit_low, bit_high=bit_high,
                                                                      value=0)
                if self.default_register_value:
                    new_bit.set_from_shifted_value(self.default_register_value)
                self._add_bit(new_bit)

    @staticmethod
    def _get_bit_scopes(missing_bits: []):
        if not missing_bits:
            return []
        index = 0
        bit_low = missing_bits[index]
        bit_scopes = []
        while index + 1 < len(missing_bits):
            if missing_bits[index + 1] > missing_bits[index] + 1:
                bit_high = missing_bits[index]
                bit_scopes.append([bit_low, bit_high])
                bit_low = missing_bits[index + 1]
            index += 1
        bit_high = missing_bits[-1]
        bit_scopes.append([bit_low, bit_high])
        return bit_scopes

    def _add_bit(self, bit):
        bit.parent = self
        super()._add_bit(bit)

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        modified = []
        old_value_property = PropertyState(PropertyState.SupportedProperties.VALUE, self.value)
        value = self.get_parsed_string_value(value)
        if value == self.value:
            return []
        modified.append((self, {old_value_property}))
        modified.extend(self._apply_value_to_bits(value))
        return modified

    def _apply_value_to_bits(self, value):
        modified = []
        for bit in self.bit_fields:
            old_value_property = PropertyState(PropertyState.SupportedProperties.VALUE, bit.value)
            changed = bit.set_from_shifted_value(value)
            if changed:
                modified.append((changed, {old_value_property}))
        return modified

    def _get_val_from_bits(self):
        if not self.bit_fields:
            return None
        value = 0
        for bit in self.bit_fields:
            value = (~bit.get_mask() & value) | bit.get_shifted_value(process_calculate=True)
        return value

    @property
    def value(self):
        return self._get_val_from_bits()

    @value.setter
    def value(self, val):
        self._apply_value_to_bits(val)

    def display_func(self, val):
        if isinstance(val, bytes) and self.display_mode == DisplayMode.HEX.value:
            return "0x" + Converter.bytes_to_string(val)
        if isinstance(val, bytes) and self.display_mode == DisplayMode.DEC.value:
            return str(int.from_bytes(val, self.byte_order))
        if isinstance(val, int) and self.display_mode == DisplayMode.HEX.value:
            value_size = self.size
            if val > self._max_value():
                value_size = (val.bit_length() + 7) // 8
            return "0x" + Converter.bytes_to_string(val.to_bytes(value_size, self.bigOrder))
        return str(val)

    def semideepcopy(self):
        copy = super().semideepcopy()
        copy._generate_missing_children()
        return copy
