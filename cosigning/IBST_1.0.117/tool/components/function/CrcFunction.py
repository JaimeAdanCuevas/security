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

import crcmod
from .IFunction import IFunction
from ...LibException import ComponentException
from ...Converter import Converter


class CrcFunction(IFunction):
    crcTypeTag = "crc_type"

    available_crc = \
        {  # (final_crc, init_crc, poly)
            'crc8': (0, 0x1, 0x107),  # CRC8-CCITT
            'crc8-init0': (0, 0x0, 0x107),  # CRC8-CCITT
            'crc16': (0, 0xffff, 0x11021),  # CRC16-CCITT
        }

    def parse_children(self, xml_node, buffer=None):
        super().parse_children(xml_node, buffer)
        self.set_size(Converter.string_to_int(self._parse_attribute(xml_node, self.sizeTag)))
        node = self._parse_node(xml_node, self.crcTypeTag)
        self.crc_type = self._parse_attribute(node, self.valueTag)
        self.crc_type = self.crc_type.lower()
        self.crc_class = None
        if self.crc_type not in self.available_crc:
            raise ComponentException("Crc type '%s' not supported, Available are: %s " % (
                self.crc_type, ', '.join(self.available_crc.keys())), self.name)

    def _build_layout(self):
        try:
            self.crc_class = crcmod.Crc(self.available_crc[self.crc_type][2],
                                        rev=False,
                                        initCrc=self.available_crc[self.crc_type][1],
                                        xorOut=self.available_crc[self.crc_type][0])
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
