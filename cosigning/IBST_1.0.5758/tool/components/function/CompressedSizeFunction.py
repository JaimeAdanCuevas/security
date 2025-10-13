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

import string

from cffi.backend_ctypes import xrange
from .IFunction import IFunction
from ...LibException import ComponentException, LibException


class CompressedSizeFunction(IFunction):

    class Tags(IFunction.Tags):
        START_OFFSET = "start_offset"
        MODULE_NAME = "module_name"
        COUNT = "count"

    sha_type = None
    startNode = None
    moduleNode = None
    countNode = None

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        self.start_node = xml_node.find(self.Tags.START_OFFSET)
        self.module_node = xml_node.find(self.Tags.MODULE_NAME)
        self.count_node = xml_node.find(self.Tags.COUNT)
        self.calculate_compressed_size(self.buffer)

    def calculate_compressed_size(self, buffer):
        # get partition start, module name and entries count
        start_offset = self.calculate_value(self.start_node.attrib[self.Tags.VALUE], allow_calculate=True)
        buffer_init_offset = buffer.tell()
        module_name = self.calculate_value(self.module_node.attrib[self.Tags.VALUE], allow_calculate=True)
        count = self.calculate_value(self.count_node.attrib[self.Tags.VALUE], allow_calculate=True)
        module_name_offset = start_offset + 16
        # find meta data for compressed module
        module_name = ''.join(filter(lambda x: x in string.printable, module_name))
        module_meta = module_name + ".met"
        buffer.seek(module_name_offset)
        try:
            for _ in xrange(count):
                # read module name from entry
                mod_name = buffer.read(12).decode("ascii")
                mod_name = mod_name.strip('\0')
                if module_meta == mod_name:
                    # metadata found read offset
                    extension_offset = int.from_bytes(buffer.read(4), self.littleOrder)
                    # read uncompressed module size from extension
                    buffer.seek(start_offset + extension_offset + 16)
                    self.value = int.from_bytes(buffer.read(4), self.littleOrder)
                    break
                buffer.seek(buffer.tell() + 12)
        except (ValueError, OverflowError, LibException) as e:
            raise ComponentException("Cannot read compressed module size") from e
        buffer.seek(buffer_init_offset)
