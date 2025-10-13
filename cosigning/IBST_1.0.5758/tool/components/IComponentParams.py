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
from enum import Enum
import json
from typing import Optional

from ..LibException import ComponentException
from ..Converter import Converter
from ..utils import bit_count, get_min_max_values


class DisplayMode(Enum):
    HEX = 'hex'
    DEC = 'dec'
    STR = 'str'


class ComponentParams:

    class ParamsAttr(Enum):
        VALUE_LIST = "value_list"
        VALUE_MIN = "value_min"
        VALUE_MAX = "value_max"
        VALUE_LEN = "value_len"
        ID_SETTING = "id_setting"
        ID_COUNTER_START = "id_counter_start"
        REQUIRED_BINARY = 'required_binary'
        NOTE_AVAILABLE = 'note_available'
        SKIP_VALUE_VALIDATION = 'skip_value_list_validation'

    _text = ''
    _name = ''

    def __init__(self, params, name, value_converter=Converter.string_to_int, component=None):
        self._set_default_attributes()
        self._text = params
        self.component: Optional['IComponent'] = component
        self._name = name
        self.value_converter = value_converter
        self._parse_params()

    def _set_default_attributes(self):
        self._required_binary = False

    @property
    def required_binary(self):
        return self.component.calculate_value(self._required_binary) if self._required_binary else False

    @required_binary.setter
    def required_binary(self, value: str):  # pylint: disable=used-before-assignment
        self._required_binary = value

    @property
    def note_available(self):
        """
        Availability of note feature should be determined by component saveability by default, unless it is set
        explicitly in params.
        """
        note_available = self.dict.get(self.ParamsAttr.NOTE_AVAILABLE.value)
        if note_available is not None:
            return Converter.string_to_bool(note_available)
        if self.component:
            if self.component.xml_save_formula:
                return self.component.is_setting_saveable and self.component.xml_save_formula_is_static
            return self.component.is_setting_saveable
        return False

    @property
    def skip_value_list_validation(self):
        return Converter.string_to_bool(self.dict[self.ParamsAttr.SKIP_VALUE_VALIDATION.value]) \
            if self.ParamsAttr.SKIP_VALUE_VALIDATION.value in self.dict else False

    @property
    def str(self):
        return json.dumps(self.dict)

    def value_str(self, param_type: ParamsAttr):
        return self.dict.get(param_type.value)

    def value_int(self, param_type: ParamsAttr):
        return int(self.value_str(param_type), 0)

    def is_min_max_set(self):
        return self.ParamsAttr.VALUE_MIN.value in self.dict and \
               self.ParamsAttr.VALUE_MAX.value in self.dict

    def is_id_setting_set(self):
        return self.ParamsAttr.ID_SETTING.value in self.dict

    def is_id_counter_start_set(self):
        return self.ParamsAttr.ID_COUNTER_START.value in self.dict

    def is_value_list(self):
        return self.ParamsAttr.VALUE_LIST.value in self.dict

    def is_in_value_list(self, value):
        return value in self.dict[self.ParamsAttr.VALUE_LIST.value].values()

    def gen_value_len(self, size):
        self.dict[self.ParamsAttr.VALUE_LEN.value] = str(size)

    def gen_value_min_max(self, size, signed=False, display_format: DisplayMode = DisplayMode.HEX):
        value_min_tag = self.ParamsAttr.VALUE_MIN.value
        value_max_tag = self.ParamsAttr.VALUE_MAX.value
        str_min, str_max = get_min_max_values(size, signed)

        if value_min_tag not in self.dict:
            self.dict[value_min_tag] = str_min
        if value_max_tag not in self.dict:
            self.dict[value_max_tag] = str_max

        if size:
            bit_len = bit_count(self.dict[value_max_tag])
            if bit_len > size * 8:
                raise ComponentException("Specified max value exceeds setting size", self._name)

        v_min = int(self.dict[value_min_tag], 0) if value_min_tag in self.dict else 0
        v_max = int(self.dict[value_max_tag], 0) if value_max_tag in self.dict else None
        if v_max is not None and v_min > v_max:
            raise ComponentException("Specified max value cannot be lower than min", self._name)
        self._format_min_max_values(v_min, v_max, display_format)

    def gen_value_min_max_from_bits(self, bit_low, bit_high, display_format: DisplayMode = DisplayMode.HEX):
        value_min_tag = self.ParamsAttr.VALUE_MIN.value
        value_max_tag = self.ParamsAttr.VALUE_MAX.value
        if bit_low < 0 or bit_high < 0:
            raise ComponentException("bit_low and bit_high cannot be negative")
        bit_size = bit_high-bit_low+1
        if bit_size <= 0:
            raise ComponentException("bit_low cannot be larger than bit_high", self._name)
        if value_min_tag not in self.dict:
            self.dict[value_min_tag] = "0x0"
        if value_max_tag not in self.dict:
            self.dict[value_max_tag] = f"0x{2 ** bit_size - 1:X}"

        bit_len = bit_count(self.dict[value_max_tag])
        if bit_len > bit_size:
            raise ComponentException("Specified max value exceeds setting size", self._name)

        v_min = int(self.dict[value_min_tag], 0) if value_min_tag in self.dict else 0
        v_max = int(self.dict[value_max_tag], 0) if value_max_tag in self.dict else None
        if v_min is not None and v_max is not None and v_min > v_max:
            raise ComponentException("Specified max value cannot be lower than min", self._name)
        self._format_min_max_values(v_min, v_max, display_format)

    def get_all_values_from_value_list(self):
        return list(self.dict['value_list'].values())

    def get_all_keys_from_value_list(self):
        return list(self.dict['value_list'].keys())

    def get_all_from_value_list(self):
        return list(self.dict['value_list'].items())

    def get_key_from_value_list(self, value):
        return next((key for key, val in self.get_all_from_value_list() if val == value), "")

    def _parse_params(self):
        json_dict = {}
        if self._text:
            self._text = self._text.replace("\'", "\"")
            json_dict = json.loads(self._text)

        if self.ParamsAttr.VALUE_LIST.value in json_dict:
            value_list = json_dict[self.ParamsAttr.VALUE_LIST.value]
            for k, v in value_list.items():
                value_list[k] = self.value_converter(v)

        self.dict = json_dict

        if self.ParamsAttr.REQUIRED_BINARY.value in json_dict:
            self.required_binary = json_dict[self.ParamsAttr.REQUIRED_BINARY.value]

    def _format_min_max_values(self, v_min, v_max, display_format: DisplayMode):
        value_min_tag = self.ParamsAttr.VALUE_MIN.value
        value_max_tag = self.ParamsAttr.VALUE_MAX.value
        if display_format == DisplayMode.DEC:
            self.dict[value_min_tag] = str(v_min)
            self.dict[value_max_tag] = str(v_max)
        else:
            self.dict[value_min_tag] = str(hex(v_min))
            self.dict[value_max_tag] = str(hex(v_max))
