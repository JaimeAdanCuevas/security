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
from .BitFieldComponent import BitFieldComponent
from ..Converter import Converter
from ..ColorPrint import ColorPrint


class BitRegisterComponent(BitFieldComponent):

    def __init__(self, xml_node, **kwargs):
        self.signed = False
        super().__init__(xml_node, **kwargs)
        if self.valueTag in xml_node.attrib:
            modified = self._apply_value_to_bits(Converter.string_to_int(xml_node.attrib[self.valueTag]))
            if modified:
                for each in modified:
                    ColorPrint.debug(f'{each.name} value was overwritten to {each.get_value_string()} to be consistent '
                                     f'with range {each.bit_low}:{each.bit_high} '
                                     f'of its parent {each.parent.name} value={each.parent.get_value_string()}')

    def parse_children(self, xml_node, buffer=None):
        super().parse_children(xml_node, buffer)
        self._generate_missing_children()

    def _generate_missing_children(self):
        missing_bits_array = list(range(0, self.size * 8))
        for bit_param in self.bit_fields:
            for bit in range(bit_param.bit_low, bit_param.bit_high + 1):
                missing_bits_array.remove(bit)
        if len(missing_bits_array):
            bit_scopes = self._get_bit_scopes(missing_bits_array)
            for bit_range in bit_scopes:
                bit_low, bit_high = bit_range
                name = f"reserved_{self.name}_{bit_low}-{bit_high}"
                new_bit = BitFieldComponent.Bit.init_without_xml_node(name=name, bit_low=bit_low, bit_high=bit_high, value=0)
                self._add_bit(new_bit)

    @staticmethod
    def _get_bit_scopes(missing_bits: []):
        if not len(missing_bits):
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

    def parse_string_value(self, value):
        modified = []
        value = self._parse_string_value(value)
        if value == self.value:
            return []
        modified.append(self)
        modified.extend(self._apply_value_to_bits(value))
        return modified

    def _apply_value_to_bits(self, value):
        modified = []
        for bit in self.bit_fields:
            changed = bit.set_from_shifted_value(value)
            if changed:
                modified.append(changed)
        return modified

    def _get_val_from_bits(self):
        if not self.bit_fields:
            return None
        else:
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
