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

from collections import namedtuple
import crcmod
from .IFunction import IFunction
from ...LibException import ComponentException


class CrcFunction(IFunction):
    # pylint: disable=line-too-long
    """Calculates CRC (cyclic redundancy check) value used to check if the data was not corrupted.

    CRC function children:

    Configurable children      Required      Description
    ---------------------      --------      -----------
    crc_type                   yes           Indicates the crc type, possible are: "crc8", "crc8-init0", "crc16", "crc32"
    """
    # pylint: enable=line-too-long

    class Tags(IFunction.Tags):
        CRC_TYPE = "crc_type"

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

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        node = self._parse_node(xml_node, self.Tags.CRC_TYPE)
        self.crc_type = self._parse_attribute(node, self.Tags.VALUE)
        self.crc_type = self.crc_type.lower()
        try:
            self.crc_class = CrcFunction.get_crc_class(self.crc_type)
        except ValueError as e:
            raise ComponentException("Problem with crc calculation occurred", self.name) from e
        self.size = self.crc_class.digest_size

    def _build_layout(self):
        if self.crc_class.digest_size > self.size:
            raise ComponentException(f"Given size ({self.size} bytes) is not enough for {self.crc_type}", self.name)
        self.set_value(self.get_default_value())

    def _build(self, buffer):
        super()._build(buffer)
        # pylint: disable-next=attribute-defined-outside-init
        self.crc_class = self.crc_class.new()  # refresh initial value
        data = self.get_input_bytes(buffer)
        self.crc_class.update(data)
        self.set_value(self.crc_class.crcValue.to_bytes(self.size, self.littleOrder))
