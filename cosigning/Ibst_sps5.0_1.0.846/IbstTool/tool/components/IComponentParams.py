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
import sys
from enum import Enum
import json
from ..LibException import ComponentException
from ..Converter import Converter
from ..utils import bit_count


class ComponentParams:
    class ParamsAttr(Enum):
        ValueList = "value_list"
        ValueMin = "value_min"
        ValueMax = "value_max"
        ValueLen = "value_len"

    _text = ''
    _name = ''

    def __init__(self, params, name):
        self._text = params
        self._name = name
        self._parse_params()

    @property
    def str(self):
        return json.dumps(self.dict)

    def value_str(self, type: ParamsAttr):
        if type.value in self.dict:
            return self.dict[type.value]

    def value_int(self, type: ParamsAttr):
        return int(self.value_str(type), 0)

    def is_min_max_set(self):
        return self.ParamsAttr.ValueMin.value in self.dict and \
               self.ParamsAttr.ValueMax.value in self.dict

    def is_value_list(self):
        return self.ParamsAttr.ValueList.value in self.dict

    def is_in_value_list(self, value):
        return value in self.dict[self.ParamsAttr.ValueList.value].values()

    def gen_value_len(self, size):
        self.dict[self.ParamsAttr.ValueLen.value] = str(size)

    def gen_value_min_max(self, size):
        value_min_tag = self.ParamsAttr.ValueMin.value
        value_max_tag = self.ParamsAttr.ValueMax.value
        if value_min_tag not in self.dict:
            self.dict[value_min_tag] = "0x0"

        if size:
            if value_max_tag not in self.dict:
                self.dict[value_max_tag] = "0x" + size * "FF"
            bit_len = bit_count(self.dict[value_max_tag])
            if bit_len > size * 8:
                raise ComponentException("Specified max value exceeds setting size", self._name)
        else:
            if value_max_tag not in self.dict:
                python_max_value = str(hex(sys.maxsize))
                self.dict[value_max_tag] = python_max_value

        v_min = int(self.dict[value_min_tag], 0) if value_min_tag in self.dict else 0
        v_max = int(self.dict[value_max_tag], 0) if value_max_tag in self.dict else None
        if v_max is not None:
            if v_min > v_max:
                raise ComponentException("Specified max value cannot be lower than min", self._name)

    def gen_value_min_max_from_bits(self, bit_low, bit_high):
        value_min_tag = self.ParamsAttr.ValueMin.value
        value_max_tag = self.ParamsAttr.ValueMax.value
        if bit_low < 0 or bit_high < 0:
            raise ComponentException("bit_low and bit_high cannot be negative")
        bit_size = bit_high-bit_low+1
        if bit_size <= 0:
            raise ComponentException("bit_low cannot be larger than bit_high", self._name)
        if value_min_tag not in self.dict:
            self.dict[value_min_tag] = "0x0"
        if value_max_tag not in self.dict:
            self.dict[value_max_tag] = "0x{0:X}".format(2 ** bit_size - 1)

        bit_len = bit_count(self.dict[value_max_tag])
        if bit_len > bit_size:
            raise ComponentException("Specified max value exceeds setting size", self._name)

        v_min = int(self.dict[value_min_tag], 0) if value_min_tag in self.dict else 0
        v_max = int(self.dict[value_max_tag], 0) if value_max_tag in self.dict else None
        if v_min is not None and v_max is not None:
            if v_min > v_max:
                raise ComponentException("Specified max value cannot be lower than min", self._name)

    def _parse_params(self):
        json_dict = {}
        if self._text:
            self._text = self._text.replace("\'", "\"")
            json_dict = json.loads(self._text)

        if self.ParamsAttr.ValueList.value in json_dict:
            value_list = json_dict[self.ParamsAttr.ValueList.value]
            for k, v in value_list.items():
                value_list[k] = Converter.string_to_int(v)

        self.dict = json_dict
