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

from .IFunction import IFunction
from ...LibException import ComponentException, LibException
from cffi.backend_ctypes import xrange
import string


class CompressedSizeFunction(IFunction):
    startOffsetTag = "start_offset"
    moduleNameTag = "module_name"
    countTag = "count"
    sha_type = None
    startNode = None
    moduleNode = None
    countNode = None

    def parse_children(self, xml_node, buffer = None):
        super().parse_children(xml_node)
        self.start_node = xml_node.find(self.startOffsetTag)
        self.module_node = xml_node.find(self.moduleNameTag)
        self.count_node = xml_node.find(self.countTag)
        if self.start_node is None:
            self._raise_missing_child(self.startOffsetTag)
        if self.module_node is None:
            self._raise_missing_child(self.moduleNameTag)
        if self.count_node is None:
            self._raise_missing_child(self.countTag)
        if self.valueTag not in self.start_node.attrib:
            raise ComponentException("Missing value for tag: '{}'".format(self.startOffsetTag), self.name)
        if self.valueTag not in self.module_node.attrib:
            raise ComponentException("Missing value for tag: '{}'".format(self.moduleNameTag), self.name)
        if self.valueTag not in self.count_node.attrib:
            raise ComponentException("Missing value for tag: '{}'".format(self.countTag), self.name)

        self.calculate_compressed_size(buffer)

    def calculate_compressed_size(self, buffer):
        # get partition start, module name and entries count
        start_offset = self.calculate_value(self.start_node.attrib[self.valueTag], allow_calculate=True)
        buffer_init_offset = buffer.tell()
        module_name = self.calculate_value(self.module_node.attrib[self.valueTag], allow_calculate=True)
        count = self.calculate_value(self.count_node.attrib[self.valueTag], allow_calculate=True)
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
        except (ValueError, OverflowError, LibException):
            raise ComponentException("Cannot read compressed module size")
        buffer.seek(buffer_init_offset)
                
        
