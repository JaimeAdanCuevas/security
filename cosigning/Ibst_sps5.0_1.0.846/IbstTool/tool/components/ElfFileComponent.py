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

import os
from enum import Enum

from .. import LibException
from .IComponent import IComponent
from ..LibException import ComponentException, LibException
from ..utils import validate_file
from ..elf import scan_ie_elf, scan_elf_with_objdump, ie_elf2bin


class ElfFileComponent(IComponent):
    class ComponentProperty(Enum):
        Code = "code"
        Data = "data"
        Bin = "bin"
        PrivateCodeBaseAddress = "private_code_base_address"
        UncompressedPrivateCodeSize = "uncompressed_private_code_size"
        BssSize = "bss_size"
        TextSize = "text_size"
        EntryAddress = "entry_address"
        TextFilsz = "text_filsz"
        TextMemsz = "text_memsz"
        TextPaddr = "text_paddr"
        TextOffset = "text_offset"
        DataFilsz = "data_filsz"
        DataMemsz = "data_memsz"
        DataPaddr = "data_paddr"
        DataOffset = "data_offset"
        ImageTextStart = "image_text_start"
        ImageTextEnd = "image_text_end"
        ImageRamStart = "image_ram_start"
        ImageRamEnd = "image_ram_end"

    moduleEntryTag = "module_entry"
    objcopyArgsTag = "objcopy_args"
    objcopyPathTag = "objcopy_path"
    objdumpArgsTag = "objdump_args"
    objdumpPathTag = "objdump_path"
    markersArgsTag = "markers"



    module_entry = None
    objcopy_args = None
    objcopy_path = None
    objdump_args = None
    objdump_path = None

    def __init__(self, xml_node, **kwargs):
        self.markers = {self.ComponentProperty.ImageTextStart.value: None,
                        self.ComponentProperty.ImageTextEnd.value: None,
                        self.ComponentProperty.ImageRamStart.value: None,
                        self.ComponentProperty.ImageRamEnd.value: None}

        super().__init__(xml_node, **kwargs)

        # lazy loaded properties
        self._set_property("elf_info")
        self._set_property("file_content")
        self._set_property("bin_content")

    def _parse_elf_file(self):
        self.validate_path()

        if self.objdump_args is not None:
            self._elf_info = self._do_objdump()
        else:
            self._elf_info = scan_ie_elf(self.value, self.module_entry, self.markers)
            self._elf_info.ie.text_start = self._elf_info.entry_address

        with open(self.value, "rb") as f:
            self._file_content = f.read()

        if self.objcopy_args is not None:
            outfile = self.value + ".bin"
            ie_elf2bin(self.value, self.objcopy_path, self.objcopy_args, outfile)
            with open(outfile, mode='rb') as f:
                self._bin_content = f.read()
            os.remove(outfile)

    def _do_objdump(self):
        # we don't get all symbols when we use objdump, only those that we needed so far
        symbols_map = {'entry_address': self.module_entry}
        symbols_map.update(self.markers)
        return scan_elf_with_objdump(self.value, self.objdump_path, self.objdump_args, symbols_map)

    def validate_path(self):
        validate_file(self.value)

    def _parse_string_value(self, value):
        self._set_value(value)
        self._elf_info = None
        return self.value

    def parse_children(self, xml_node, buffer=None):
        module_entry_node = xml_node.find(self.moduleEntryTag)
        if module_entry_node is None or self.valueTag not in module_entry_node.attrib:
            raise ComponentException("'{}' child tag with proper value attribute is "
                                     "required for this component"
                                     .format(self.moduleEntryTag), self.name)

        self.module_entry = module_entry_node.attrib[self.valueTag]

        # if user specified arguments for objcopy then use it to retrieve bin data from elf
        objcopy_args_node = xml_node.find(self.objcopyArgsTag)
        if objcopy_args_node is not None:
            if self.valueTag not in objcopy_args_node.attrib:
                raise ComponentException("'{}' tag requires '{}' attribute"
                                         .format(self.objcopyArgsTag, self.valueTag), self.name)
            self.objcopy_args = objcopy_args_node.attrib[self.valueTag]

        self.objcopy_path = ""
        objcopy_path_node = xml_node.find(self.objcopyPathTag)
        if objcopy_path_node is not None:
            if self.valueTag not in objcopy_path_node.attrib:
                raise ComponentException("'{}' tag requires '{}' attribute"
                                         .format(self.objcopyPathTag, self.valueTag), self.name)
            self.objcopy_path = objcopy_path_node.attrib[self.valueTag]

        self.objdump_path = ""
        objdump_path_node = xml_node.find(self.objdumpPathTag)
        if objdump_path_node is not None:
            if self.valueTag not in objdump_path_node.attrib:
                raise ComponentException("'{}' tag requires '{}' attribute"
                                         .format(self.objdumpPathTag, self.valueTag), self.name)
            self.objdump_path = objdump_path_node.attrib[self.valueTag]

        # if user specified arguments for objdump then use it to retrieve offsets from elf
        objdump_args_node = xml_node.find(self.objdumpArgsTag)
        if objdump_args_node is not None:
            if self.valueTag not in objdump_args_node.attrib:
                raise ComponentException("'{}' tag requires '{}' attribute"
                                         .format(self.objdumpArgsTag, self.valueTag), self.name)
            self.objdump_args = objdump_args_node.attrib[self.valueTag]

        markers_node = xml_node.findall(self.markersArgsTag + '/*')
        if markers_node:
            for marker in markers_node:
                if self.valueTag not in marker.attrib:
                    raise ComponentException("'{}' child tag with proper value attribute is "
                                             "required for this component"
                                             .format(self.markersArgsTag), self.name)
                self.markers[marker.tag] = marker.attrib[self.valueTag]

    def _get_property(self, component_property, _=False):
        if component_property == self.ComponentProperty.Code:
            start = self.elf_info.ie.text_offset
            size = self.elf_info.ie.text_filsz
            return self.file_content[start: start + size]
        if component_property == self.ComponentProperty.Data:
            start = self.elf_info.ie.data_offset
            size = self.elf_info.ie.data_filsz
            return self.file_content[start: start + size]
        if component_property == self.ComponentProperty.Bin:
            return self.bin_content
        if component_property == self.ComponentProperty.PrivateCodeBaseAddress:
            return self.elf_info.private_code_base_address
        if component_property == self.ComponentProperty.UncompressedPrivateCodeSize:
            return self.elf_info.uncompressed_private_code_size
        if component_property == self.ComponentProperty.BssSize:
            return self.elf_info.bss_size
        if component_property == self.ComponentProperty.TextSize:
            return self.elf_info.text_size
        if component_property == self.ComponentProperty.EntryAddress:
            return self.elf_info.entry_address
        if component_property == self.ComponentProperty.DataFilsz:
            return self.elf_info.ie.data_filsz
        if component_property == self.ComponentProperty.DataMemsz:
            return self.elf_info.ie.data_memsz
        if component_property == self.ComponentProperty.DataPaddr:
            return self.elf_info.ie.data_paddr
        if component_property == self.ComponentProperty.DataOffset:
            return self.elf_info.ie.data_offset
        if component_property == self.ComponentProperty.TextFilsz:
            return self.elf_info.ie.text_filsz
        if component_property == self.ComponentProperty.TextMemsz:
            return self.elf_info.ie.text_memsz
        if component_property == self.ComponentProperty.TextPaddr:
            return self.elf_info.ie.text_paddr
        if component_property == self.ComponentProperty.TextOffset:
            return self.elf_info.ie.text_offset
        if component_property == self.ComponentProperty.ImageTextStart:
            return self.elf_info.image_text_start
        if component_property == self.ComponentProperty.ImageTextEnd:
            return self.elf_info.image_text_end
        if component_property == self.ComponentProperty.ImageRamStart:
            return self.elf_info.image_ram_start
        if component_property == self.ComponentProperty.ImageRamEnd:
            return self.elf_info.image_ram_end

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst.objcopy_args = self.objcopy_args
        dst.objcopy_path = self.objcopy_path
        dst.objdump_args = self.objdump_args
        dst.objdump_path = self.objdump_path
        dst.module_entry = self.module_entry
        dst.markers = dict(self.markers)

    @classmethod
    def _set_property(cls, property_name):  # set
        attr_name = "_" + property_name

        def _lazy_get(self):
            attr = getattr(self, attr_name, None)
            if attr is None:
                self._parse_elf_file()
            return getattr(self, attr_name)

        setattr(cls, attr_name, None)
        setattr(cls, property_name, property(fget=_lazy_get))
