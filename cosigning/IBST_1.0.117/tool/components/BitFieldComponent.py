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

import xml.etree.ElementTree as ElementTree

from .NumberComponent import NumberComponent
from ..LibException import ComponentException, LibException
from ..Converter import Converter
from .IComponent import IComponent


class BitFieldComponent(NumberComponent):
    BitTag = "bit"
    SetBitsTag = "set_bits"

    children_allowed = True
    set_bits = None

    class Bit(NumberComponent):

        BitLowTag = "bit_low"
        BitHighTag = "bit_high"
        XmlNodeFormat = '<bit name="{0}" bit_low="{1}" bit_high="{1}" value="{2}" />'

        bit_low = None
        bit_high = None

        def __init__(self, xml_node, **kwargs):
            super().__init__(xml_node, **kwargs)
            passed_value = kwargs.get('value')
            if passed_value is not None:
                self.value = int.from_bytes(passed_value, self.littleOrder)
                self.value = self.value & self.get_mask()
                self.value = self.value >> self.bit_low

        def _parse_additional_attributes(self, xml_node):
            if self.BitLowTag in xml_node.attrib:
                self.bit_low = Converter.string_to_int(xml_node.attrib[self.BitLowTag])

            if self.BitHighTag in xml_node.attrib:
                self.bit_high = Converter.string_to_int(xml_node.attrib[self.BitHighTag])

        def validate(self):
            if self.align_formula is not None:
                raise ComponentException("Bit field cannot have '{}' attribute"
                                         .format(self.alignTag), self.name)
            if self.size is not None:
                raise ComponentException("Bit field cannot have '{}' attribute"
                                         .format(self.sizeTag), self.name)
            if self.bit_low is None:
                raise ComponentException("'{}' is not defined".format(self.BitLowTag), self.name)
            if self.bit_high is None:
                raise ComponentException("'{}' is not defined".format(self.BitHighTag), self.name)

            if not self.parent or (self.parent and self.parent.buffer is None):
                if self.value is None and self.value_formula is None:
                    raise ComponentException("Neither '{}' nor '{}' is defined in bit field"
                                         .format(self.valueTag,
                                                 self.calculateTag),
                                         self.name)

        def get_mask(self):
            bit_size = self.bit_high - self.bit_low + 1
            return ((1 << bit_size) - 1) << self.bit_low

        def get_shifted_value(self):
            shifted_value = self.value << self.bit_low
            if shifted_value & self.get_mask() != shifted_value:
                raise ComponentException("Bit field value '{}' is too big for bit range {}:{}"
                                         .format(self.value, self.bit_low, self.bit_high),
                                         self.name)
            return shifted_value

        # we have to use whole bit_field to write and get bytes functions
        def _write_bytes(self, comp_bytes, buffer, offset=None):
            self.parent._build(buffer)
            super()._write_bytes(self.parent.get_bytes(), buffer, self.parent.offset)

        def get_bytes(self):
            return self.parent.get_bytes()

    def __init__(self, xml_node, **kwargs):
        self.bit_fields = []
        self.bit_fields_by_name = {}
        super().__init__(xml_node, **kwargs)

    def validate(self):
        IComponent.validate(self)

        # Check if either 'set_bits' attribute or 'bit' children and/or value were specified
        if self.children_allowed and not self.bit_fields and self.value is None and self.value_formula is None:
            raise ComponentException("Use either 'set_bits' attribute, 'calculate' attribute or 'bit' child nodes to define value", self.name)

        # Validate bits' coverage / range only if size was specified
        # Size doesn't have to be specified for settings
        # Coverage doesn't have to be full if value is specified
        if self.data_size is not None and self.value is None and self.value_formula is None:
            usage = 0
            for bit_field in self.bit_fields:
                if (usage & bit_field.get_mask()) != 0:
                    raise ComponentException("Bit field '{}' ({}:{}) overlaps with other bit fields"
                                             .format(str(bit_field),
                                                     bit_field.bit_low,
                                                     bit_field.bit_high),
                                             self.name)

                usage |= bit_field.get_mask()

            if usage > (1 << (self.data_size * 8)) - 1:
                raise ComponentException("Size is too small for defined bit fields", self.name)

            # All bits must be covered if bits are defined by child nodes, if 'set_bits' attribute is used then there is no such requirement
            if self.children_allowed:
                for i in range(self.data_size * 8):
                    if ((usage >> i) & 1) == 0:
                        raise ComponentException("Bit {} is undefined".format(i), self.name)
        elif self.data_size is not None and self.bit_fields:
            # if we don't validate coverage and there are some bit_fields we need at least verify
            # that bit range is within size
            max_bit = max([bit.bit_high for bit in self.bit_fields])
            if max_bit >= self.size*8:
                raise ComponentException(f"{self.Bit.BitHighTag}: {max_bit} is out of range for size {self.data_size}",
                                         self.name)

    def parse_children(self, xml_node, buffer=None):
        bit_nodes = xml_node.findall(self.BitTag)
        if not self.children_allowed and bit_nodes:
            raise ComponentException(
                "'bit_field' can have either '{}' attribute or '{}' child nodes, but not both".format(self.SetBitsTag,
                                                                                                      self.BitTag),
                self.name)
        self.children = []
        self.children_by_name = {}
        buffer_value = None
        if buffer is not None:
            buffer_value = self.value
        try:
            for bit_node in bit_nodes:
                bit = self.Bit(bit_node, value=buffer_value, parent=self)
                bit.validate()
                self._add_bit(bit)
        except LibException as ex:
            self.trace_exception(ex)

    def _add_bit(self, bit):
        self.bit_fields.append(bit)
        self.bit_fields_by_name[bit.name] = bit

    def _parse_additional_attributes(self, xml_node):
        if self.SetBitsTag in xml_node.attrib:
            self.set_bits = xml_node.attrib[self.SetBitsTag]
            self.children_allowed = False
            bit_str_indeces = [str_index.strip() for str_index in self.set_bits.split('|')]
            for str_index in bit_str_indeces:
                index = Converter.string_to_int(str_index)
                name = "bit{}".format(index)
                bit_node_str = self.Bit.XmlNodeFormat.format(name, index, 1)
                bit_node = ElementTree.fromstring(bit_node_str)
                bit = self.Bit(bit_node)
                bit.validate()
                self._add_bit(bit)

            # If user gave bit indices then we can immediately calculate the value of whole structure
            value = 0
            for bit in self.bit_fields:
                value |= bit.get_shifted_value()

            self._set_value(value)

    def _parse_string_value(self, value):
        if self.set_bits is None:
            return super()._parse_string_value(value)
        return value

    def _build_layout(self):
        if self.data_size is None:
            raise ComponentException("Size is not defined", self.name)

        if self.value is None:
            self._set_value(self.get_default_value())

    def get_child(self, child_name):
        if child_name in self.bit_fields_by_name:
            return self.bit_fields_by_name[child_name]
        return None

    def _build(self, buffer):
        super()._build(buffer)
        value = self.value if self.value is not None else 0

        try:
            for bit in self.bit_fields:
                bit.build(buffer)

                value = (~bit.get_mask() & value) | bit.get_shifted_value()
            self._set_value(value)
        except LibException as ex:
            self.trace_exception(ex)
