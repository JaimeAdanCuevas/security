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

import crcmod
from collections import namedtuple
from .IFunction import IFunction
from ...LibException import ComponentException
from ...Converter import Converter


class CrcFunction(IFunction):
    crcTypeTag = "crc_type"

    CrcDefinition = namedtuple('CrcDefinition', ['xorOut', 'initCrc', 'poly', 'rev'])
    available_crc = \
        {  # (final_crc, init_crc, poly, reversed)
            'crc8': CrcDefinition(xorOut=0, initCrc=0x1, poly=0x107, rev=False),  # CRC8-CCITT
            'crc8-init0': CrcDefinition(xorOut=0, initCrc=0x0, poly=0x107, rev=False),  # CRC8-CCITT
            'crc16': CrcDefinition(xorOut=0, initCrc=0xffff, poly=0x11021, rev=False),  # CRC16-CCITT
            'crc32': CrcDefinition(xorOut=0xffffffff, initCrc=0, poly=0x104C11DB7, rev=True),  # CRC32
        }

    @staticmethod
    def get_crc_class(crc_name):
        if crc_name not in CrcFunction.available_crc:
            raise ComponentException(f"Crc type '{crc_name}' is not supported, "
                                     f"Available are: {', '.join(CrcFunction.available_crc.keys())}")
        crc_class = crcmod.Crc(**CrcFunction.available_crc[crc_name]._asdict())
        return crc_class

    def parse_children(self, xml_node, buffer=None):
        super().parse_children(xml_node, buffer)
        self.size = Converter.string_to_int(self._parse_attribute(xml_node, self.sizeTag))
        node = self._parse_node(xml_node, self.crcTypeTag)
        self.crc_type = self._parse_attribute(node, self.valueTag)
        self.crc_type = self.crc_type.lower()
        self.crc_class = None

    def _build_layout(self):
        try:
            self.crc_class = CrcFunction.get_crc_class(self.crc_type)
        except ValueError as e:
            raise ComponentException("Problem with crc calculation occurred", self.name)
        if self.crc_class.digest_size > self.size:
            raise ComponentException("Given size (%s bytes) is not enough for %s" % (self.size, self.crc_type),
                                     self.name)
        self._set_value(self.get_default_value())

    def _build(self, buffer):
        super()._build(buffer)
        self.crc_class = self.crc_class.new() #refresh initial value
        data = self.get_input_bytes()
        self.crc_class.update(data)
        self._set_value(self.crc_class.crcValue.to_bytes(self.size, self.littleOrder))
