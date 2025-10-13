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
from typing import List, Optional

from lxml.etree import fromstring  # nosec - we parse only known internal content

from .NumberComponent import NumberComponent
from ..ColorPrint import log
from ..LibException import ComponentException, LibException, ValidateException
from ..Converter import Converter
from .IComponent import IComponent
from ..PropertyState import PropertyState, ComponentPreChangeState


class BitFieldComponent(NumberComponent):
    """Component that can be used in order to define a byte structure "bit by bit" using bit components,
    whose bit_low and bit_high attributes can be filled to tell the bit range that should be covered.
    For example:

    ```xml
    <bit_field name="two_bytes" size="2" >
        <bit name="one_bit" bit_low="0" bit_high="0" value="0" />
        <bit name="two_bits" bit_low="1" bit_high="2" value="2" />
        <bit name="seven_bits" bit_low="3" bit_high="9" value="0x7F" />
        <bit name="special_bit" bit_low="10" bit_high="10" calculate="/settings/special_bit.value" />
        <bit name="reserved" bit_low="11" bit_high="15" value="0" />
    </bit_field>
    ```

    Note: bit numeration starts with 0
    """

    class Tags(NumberComponent.Tags):
        BIT = "bit"
        SET_BITS = "set_bits"

    children_allowed = True
    set_bits = None

    class Bit(NumberComponent):
        bit_low = None
        bit_high = None

        def __init__(self, xml_node, **kwargs):
            super().__init__(xml_node, **kwargs)
            passed_value = kwargs.get('value')
            if passed_value is not None:
                self.set_value_from_parent_value(passed_value)
            if self.params:
                self._assign_min_max_values()

        @staticmethod
        def init_without_xml_node(name: str, bit_low: int, bit_high: int, value: int = 0):
            xml_node_format = '<bit name="{0}" bit_low="{1}" bit_high="{2}" value="{3}" />'
            bit_node_str = xml_node_format.format(name, bit_low, bit_high, value)
            bit_node = fromstring(bit_node_str)  # nosec
            return BitFieldComponent.Bit(bit_node)

        def set_value_from_parent_value(self, parent_value):
            value = parent_value & self.get_mask()
            self.value = value >> self.bit_low

        # Bits should not be saved in configuration at all. Configuration should hold bit's parent value only
        @property
        def is_setting_saveable(self):
            return False

        def get_bit_count(self) -> Optional[int]:
            if self.bit_low is not None and self.bit_high is not None:
                return self.bit_high - self.bit_low + 1
            return None

        def _parse_additional_attributes(self, xml_node):
            super()._parse_additional_attributes(xml_node)
            if self.Tags.BIT_LOW in xml_node.attrib:
                self.bit_low = Converter.string_to_int(xml_node.attrib[self.Tags.BIT_LOW])

            if self.Tags.BIT_HIGH in xml_node.attrib:
                self.bit_high = Converter.string_to_int(xml_node.attrib[self.Tags.BIT_HIGH])

        def validate(self):
            if self.bit_low > self.bit_high:
                raise ComponentException(
                    f'Wrong parameter attributes: bit_low={self.bit_low} > bit_high={self.bit_high} in {self.name}')

            if not self.parent or (self.parent and not self.parent.is_decomposition_node):
                if self.value is None and self.value_formula is None:
                    raise ComponentException(f"Neither '{self.Tags.VALUE}' nor '{self.Tags.CALCULATE}' "
                                             f"is defined in bit field", self.name)

        def get_mask(self):
            bit_size = self.bit_high - self.bit_low + 1
            return ((1 << bit_size) - 1) << self.bit_low

        def get_shifted_value(self, process_calculate=False):
            if process_calculate:
                val = self.value if not self.value_formula else self.calculate_value(self.value_formula, True)
            else:
                val = self.value
            shifted_value = val << self.bit_low
            if shifted_value & self.get_mask() != shifted_value:
                raise ComponentException(f"Bit field value '{self.display_func(self.value)}' is too big for bit range "
                                         f"{self.bit_low}:{self.bit_high}", self.name)
            return shifted_value

        def set_from_shifted_value(self, val):
            val = val & self.get_mask()
            unshifted_value = val >> self.bit_low
            if self.value != unshifted_value:
                self.set_value(unshifted_value)
                return self
            return None

        def parse_string_value(self, value) -> List[ComponentPreChangeState]:
            prev = self.value
            parent_value_property = PropertyState(PropertyState.SupportedProperties.VALUE,
                                                  self.parent.value) if self.parent else None
            bit_parse_string_value_result = super().parse_string_value(value)
            if prev == self.value:
                return []
            return [bit_parse_string_value_result[0], (self.parent, {parent_value_property})]

        # we have to use whole bit_field to write and get bytes functions
        def write_bytes_to_buffer(self, comp_bytes, buffer, offset=None):
            self.parent._build(buffer)  # pylint: disable=protected-access
            super().write_bytes_to_buffer(self.parent.get_bytes(), buffer, self.parent.offset)

        def get_bytes(self):
            return self.parent.get_bytes()

        def update_from_buffer(self, buffer, current_offset=0):
            # Bits are updated in a different manner
            return current_offset

        def set_value(self, value):
            # we allow changing bits although they don't fit to the value list - registers have higher priority
            try:
                super().set_value(value)
            except ValidateException as e:
                if e.value_list:  # pylint: disable=duplicate-code
                    validate_str = f"Possible values: {e.value_list}"
                    err_str = "does not match any value from the list"
                elif e.min_max:
                    validate_str = f"Limit value: {e.min_max}"
                    err_str = "exceeds the limit value"
                max_possible_val = (2 ** (self.bit_high - self.bit_low + 1)) - 1
                # we cannot force value in case it does not fit in bit range
                if value > max_possible_val:
                    raise e
                if not self.params.skip_value_list_validation:
                    raise e
                log().warning(f"Value '{e.value}' from '{e.object_name}' {err_str} - "
                               f"forcing value from register\n{validate_str}.")
                self.value = value

        def _reset_min_max_values(self):
            if self.params.dict.get("value_min") is not None:
                self.params.dict.pop("value_min")
            if self.params.dict.get("value_max") is not None:
                self.params.dict.pop("value_max")

        def _assign_min_max_values(self):
            self._reset_min_max_values()  # reset values incorrectly assigned by parent class
            self.params.gen_value_min_max_from_bits(self.bit_low, self.bit_high, self.display_mode)

    def __init__(self, xml_node, **kwargs):
        self.bit_fields = []
        self.bit_fields_by_name = {}
        self.default_set_bits = None
        super().__init__(xml_node, **kwargs)

    def semideepcopy(self):
        copy = super().semideepcopy()
        copy.bit_fields.clear()
        copy.bit_fields_by_name.clear()
        for bit in copy.children:
            copy.bit_fields.append(bit)
            copy.bit_fields_by_name[bit.name] = bit
        return copy

    def validate(self):
        IComponent.validate(self)

        # Check if either 'set_bits' attribute or 'bit' children and/or value were specified
        if self.children_allowed and not self.bit_fields and self.value is None and self.value_formula is None:
            raise ComponentException("Use either 'set_bits' attribute, 'calculate' attribute or "
                                     "'bit' child nodes to define value", self.name)

        # Validate bits' coverage / range only if size was specified
        # Size doesn't have to be specified for settings
        # Coverage doesn't have to be full if value is specified
        if self.size is not None and self.value is None and self.value_formula is None:
            usage = 0
            for bit_field in self.bit_fields:
                if (usage & bit_field.get_mask()) != 0:
                    raise ComponentException(f"Bit field '{str(bit_field)}' ({bit_field.bit_low}:{bit_field.bit_high}) "
                                             f"overlaps with other bit fields", self.name)
                usage |= bit_field.get_mask()

            if usage > (1 << (self.size * 8)) - 1:
                raise ComponentException("Size is too small for defined bit fields", self.name)

            # All bits must be covered if bits are defined by child nodes,
            # if 'set_bits' attribute is used then there is no such requirement
            if self.children_allowed:
                for i in range(self.size * 8):
                    if ((usage >> i) & 1) == 0:
                        raise ComponentException(f"Bit {i} is undefined", self.name)
        elif self.size is not None and self.bit_fields:
            # if we don't validate coverage and there are some bit_fields we need at least verify
            # that bit range is within size
            max_bit = max(bit.bit_high for bit in self.bit_fields)
            if max_bit >= self.size*8:
                raise ComponentException(f"{self.Bit.Tags.BIT_HIGH}: {max_bit} is out of range for size {self.size}",
                                         self.name)

    def _parse_children(self, xml_node, **kwargs):
        bit_nodes = xml_node.findall(self.Tags.BIT)
        if not self.children_allowed and bit_nodes:
            raise ComponentException(f"'bit_field' can have either '{self.Tags.SET_BITS}' attribute "
                                     f"or '{self.Tags.BIT}' child nodes, but not both", self.name)
        self.children = []
        self.children_by_name = {}
        buffer_value = None
        if self.buffer is not None:
            buffer_value = int.from_bytes(self.value, self.littleOrder)
        try:
            for bit_node in bit_nodes:
                bit = self.Bit(bit_node, value=buffer_value, parent=self, skip_calculates=self._skip_calculates)
                bit.validate()
                self._add_bit(bit)
        except LibException as ex:
            self.trace_exception(ex)

    def _add_bit(self, bit):
        self.bit_fields.append(bit)
        self.bit_fields_by_name[bit.name] = bit

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        if self.Tags.SET_BITS in xml_node.attrib:
            set_bits = xml_node.attrib[self.Tags.SET_BITS]
            self.default_set_bits = set_bits
            value = self.resolve_set_bits(set_bits)
            self.set_value(value)

    def resolve_set_bits(self, set_bits):
        bit_str_indeces = [str_index.strip() for str_index in set_bits.split('|')]
        self._clear_bits()
        self.set_bits = set_bits
        self.children_allowed = False
        if not bit_str_indeces or all(bit == '' for bit in bit_str_indeces):
            # if set_bits does not contain value we are setting 0 as default
            return 0
        for str_index in bit_str_indeces:
            index = Converter.string_to_int(str_index)
            name = f"bit{index}"
            bit = self.Bit.init_without_xml_node(bit_low=index, bit_high=index, name=name, value=1)
            bit.validate()
            self._add_bit(bit)

        # If user gave bit indices then we can immediately calculate the value of whole structure
        value = 0
        for bit in self.bit_fields:
            value |= bit.get_shifted_value()

        return value

    @staticmethod
    def _access_bit(byte_array, index):
        """
        Allows to access any bit in byte array
        :param byte_array: input array of bytes
        :param index: index of bit to access
        :return: bit on selected index
        """
        base = int(index // 8)
        shift = int(index % 8)
        return (byte_array[base] & (1 << shift)) >> shift

    def _retrieve_used_bits(self):
        converted_bytes = Converter.to_bytes(self.value, self.size)
        set_bits = []
        bits = [self._access_bit(converted_bytes, i) for i in range(len(converted_bytes) * 8)]
        for idx, bit in enumerate(bits):
            if bit == 1:
                set_bits.append(idx)
        return set_bits

    def retrieve_set_bits(self):
        set_bits = '|'.join(str(bit) for bit in self._retrieve_used_bits())
        self.resolve_set_bits(set_bits)

    def _clear_bits(self):
        self.bit_fields.clear()
        self.bit_fields_by_name.clear()

    def get_parsed_string_value(self, value):
        if self.set_bits is None:
            return super().get_parsed_string_value(value)
        return value

    def _build_layout(self):
        if self.size is None:
            raise ComponentException("Size is not defined", self.name)

        if self.value is None:
            self.set_value(self.get_default_value())

    def get_child(self, child_name):
        if child_name in self.bit_fields_by_name:
            return self.bit_fields_by_name[child_name]
        raise ComponentException(f"'{self.name}' does not have '{child_name}' child.")

    def _build(self, buffer):
        super()._build(buffer)
        value = self.value if self.value is not None else 0

        try:
            for bit in self.bit_fields:
                bit.build(buffer)

                value = (~bit.get_mask() & value) | bit.get_shifted_value()
            self.set_value(value)
        except LibException as ex:
            self.trace_exception(ex)

    def update_from_buffer(self, buffer, current_offset=0):
        current_offset = super().update_from_buffer(buffer, current_offset)
        for bit in self.bit_fields:
            bit.set_value_from_parent_value(self.value)

        return current_offset

    def _validate_value_list(self, value):
        if self.set_bits is not None:
            for bit in self.bit_fields:
                if bit.bit_low == bit.bit_high:
                    super()._validate_value_list(bit.bit_low)
                else:
                    raise ValidateException("bit_low and bit_high are not equal in set_bits attribute value.", value)
        else:
            super()._validate_value_list(value)

    def get_val_string(self, val):
        if isinstance(val, bytes):
            return Converter.bytes_to_string(val)
        if self.set_bits is not None and isinstance(val, int):
            return Converter.bytes_to_string(val.to_bytes(self.size, self.byte_order))
        return super().get_val_string(val)

    def set_value(self, value):
        if self.set_bits is not None and isinstance(value, str):
            super().set_value(Converter.string_to_bytes(value))
        else:
            super().set_value(value)

    def display_func(self, val):
        return self.get_val_string(val).upper().replace("X", "x")
