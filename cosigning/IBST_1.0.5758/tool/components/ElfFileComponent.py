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

import os
from enum import Enum
from typing import List

from ..FileManager import FileManager
from ..FileOpener import open_file
from .IComponent import IComponent
from ..LibException import ComponentException, FileException
from ..PropertyState import ComponentPreChangeState
from ..elf import scan_ie_elf, scan_elf_with_objdump, ie_elf2bin
from ..ColorPrint import log


class ElfFileComponent(IComponent):
    """Component used in order to parse .elf module files and extract specific data from them.
    There is one required child node 'module_entry' and one optional child node 'markers' which children can be set to
    proper markers of 'image_text_start', 'image_text_end', 'image_ram_start' or 'image_ram_end'.
    For example:

    ```xml
    <elf_file name="rbe_elf" value="C:/data/anl/rbe_ie.elf">
        <module_entry value="rbe_entry" />
        <markers>
            <image_text_start value="image_text_start" />
            <image_text_end value="image_text_end" />
            <image_ram_start value="image_ram_start" />
            <image_ram_end value="image_ram_end" />
        </markers>
    </elf_file>
    ```

    A lot of specific data can be retrieved using special component properties: code, data, bin,
    private_code_base_address, uncompressed_private_code_size, bss_size, text_size, entry_address, text_filsz,
    text_memsz, ptext_paddr, text_offset, data_filsz, data_memsz, data_paddr, data_offset, image_text_start,
    image_text_end, image_ram_start, image_ram_end.
    """

    class ComponentProperty(Enum):
        CODE = "code"
        DATA = "data"
        BIN = "bin"
        PRIVATE_CODE_BASE_ADDRESS = "private_code_base_address"
        UNCOMPRESSED_PRIVATE_CODE_SIZE = "uncompressed_private_code_size"
        BSS_SIZE = "bss_size"
        TEXT_SIZE = "text_size"
        ENTRY_ADDRESS = "entry_address"
        TEXT_FILSZ = "text_filsz"
        TEXT_MEMSZ = "text_memsz"
        TEXT_PADDR = "text_paddr"
        TEXT_OFFSET = "text_offset"
        DATA_FILSZ = "data_filsz"
        DATA_MEMSZ = "data_memsz"
        DATA_PADDR = "data_paddr"
        DATA_OFFSET = "data_offset"
        IMAGE_TEXT_START = "image_text_start"
        IMAGE_TEXT_END = "image_text_end"
        IMAGE_RAM_START = "image_ram_start"
        IMAGE_RAM_END = "image_ram_end"

    class Tags(IComponent.Tags):
        MODULE_ENTRY = "module_entry"
        USE_OBJCOPY = "use_objcopy"
        OBJCOPY_ARGS = "objcopy_args"
        OBJCOPY_PATH = "objcopy_path"
        USE_OBJDUMP = "use_objdump"
        OBJDUMP_ARGS = "objdump_args"
        OBJDUMP_PATH = "objdump_path"
        MARKERS_ARGS = "markers"

    module_entry = None
    defaultObjcopyArgs = '-O binary'
    defaultObjdumpArgs = '-t'
    objcopy_args = None
    objdump_args = None
    use_objcopy = False
    use_objdump = False

    def __init__(self, xml_node, **kwargs):
        self.markers = {self.ComponentProperty.IMAGE_TEXT_START.value: None,
                        self.ComponentProperty.IMAGE_TEXT_END.value: None,
                        self.ComponentProperty.IMAGE_RAM_START.value: None,
                        self.ComponentProperty.IMAGE_RAM_END.value: None}

        super().__init__(xml_node, **kwargs)

        # lazy loaded properties
        self._set_property("elf_info")
        self._set_property("file_content")
        self._set_property("bin_content")

    def _parse_elf_file(self):
        self.validate_path()

        # pylint: disable=attribute-defined-outside-init
        if self.use_objdump:
            self._elf_info = self._do_objdump()
        else:
            self._elf_info = scan_ie_elf(self.value, self.module_entry, self.markers)
            self._elf_info.ie.text_start = self._elf_info.entry_address

        with open_file(self.value, "rb") as f:
            self._file_content = f.read()

        if self.use_objcopy:
            outfile = self.value + ".bin"
            ie_elf2bin(self.value, None, self.objcopy_args, outfile)
            with open_file(outfile, mode='rb') as f:
                self._bin_content = f.read()
            os.remove(outfile)
        # pylint: enable=attribute-defined-outside-init

    def _do_objdump(self):
        # we don't get all symbols when we use objdump, only those that we needed so far
        symbols_map = {'entry_address': self.module_entry}
        symbols_map.update(self.markers)
        return scan_elf_with_objdump(self.value, None, self.objdump_args, symbols_map)

    def validate_path(self):
        try:
            FileManager.validate_path_to_open(self.value)
        except FileException as ex:
            raise ComponentException(ex.message, self.display_name) from None

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        self._elf_info = None
        return super().parse_string_value(value)

    def get_parsed_string_value(self, value):
        return value

    def _parse_children(self, xml_node, **kwargs):
        module_entry_node = xml_node.find(self.Tags.MODULE_ENTRY)
        if module_entry_node is None or self.Tags.VALUE not in module_entry_node.attrib:
            raise ComponentException(f"'{self.Tags.MODULE_ENTRY}' child tag with proper value attribute is "
                                     f"required for this component", self.name)

        self.module_entry = module_entry_node.attrib[self.Tags.VALUE]

        self._parse_objcopy_settings(xml_node)
        self._parse_objdump_settings(xml_node)

        markers_node = xml_node.findall(self.Tags.MARKERS_ARGS + '/*')
        if markers_node:
            for marker in markers_node:
                if self.Tags.VALUE not in marker.attrib:
                    raise ComponentException(f"'{self.Tags.MARKERS_ARGS}' child tag with proper value attribute is "
                                             f"required for this component", self.name)
                self.markers[marker.tag] = marker.attrib[self.Tags.VALUE]

    def _parse_objcopy_settings(self, xml_node):
        use_objcopy_node = xml_node.find(self.Tags.USE_OBJCOPY)
        if use_objcopy_node is None:
            self.use_objcopy = self._parse_legacy_objcopy_settings(xml_node)
            return
        self.use_objcopy = True
        self.objcopy_args = self.defaultObjcopyArgs
        change_section_lma_node = use_objcopy_node.find('change_section_lma')
        if change_section_lma_node is not None:
            change_section_lma = self._parse_attribute(change_section_lma_node, self.Tags.VALUE, False)
            if change_section_lma is not None:
                self.objcopy_args += f' --change-section-lma {change_section_lma}'

    def _parse_legacy_tool_settings(self, xml_node, tool_name, args_tag, default_args, path_tag):
        args_node = xml_node.find(args_tag)
        if args_node is None:
            return False

        if self.Tags.VALUE not in args_node.attrib:
            raise ComponentException(f"'{args_tag}' tag requires '{self.Tags.VALUE}' attribute", self.name)
        args_in_xml = args_node.attrib[self.Tags.VALUE]
        if args_in_xml != default_args:
            log().warning(f'Specified arguments for {tool_name} will not be used: {args_in_xml}\n'
                               f'Default arguments will be used instead: {default_args}.\n'
                               f"It's not supported to specify arguments for {tool_name} anymore.")

        path_node = xml_node.find(path_tag)
        if path_node is not None:
            if self.Tags.VALUE not in path_node.attrib:
                raise ComponentException(f"'{path_tag}' tag requires '{self.Tags.VALUE}' attribute", self.name)
            path_in_xml = path_node.attrib[self.Tags.VALUE]
            if path_in_xml:
                log().warning(f'Specified path to {tool_name} will not be used: {path_in_xml}\n'
                                   f"It's not supported to specify path to {tool_name} anymore.")

        return True

    def _parse_legacy_objcopy_settings(self, xml_node):
        # if user specified arguments for objcopy then use it to retrieve bin data from elf
        use_objcopy = self._parse_legacy_tool_settings(xml_node=xml_node, tool_name='objcopy',
                                                       args_tag=self.Tags.OBJCOPY_ARGS,
                                                       default_args=self.defaultObjcopyArgs,
                                                       path_tag=self.Tags.OBJCOPY_PATH)
        if use_objcopy:
            self.objcopy_args = self.defaultObjcopyArgs
        return use_objcopy

    def _parse_objdump_settings(self, xml_node):
        use_objdump_node = xml_node.find(self.Tags.USE_OBJDUMP)
        if use_objdump_node is None:
            self.use_objdump = self._parse_legacy_objdump_settings(xml_node)
            return
        self.use_objdump = True
        self.objdump_args = self.defaultObjdumpArgs

    def _parse_legacy_objdump_settings(self, xml_node):
        # if user specified arguments for objdump then use it to retrieve bin data from elf
        use_objdump = self._parse_legacy_tool_settings(xml_node=xml_node, tool_name='objdump',
                                                       args_tag=self.Tags.OBJDUMP_ARGS,
                                                       default_args=self.defaultObjdumpArgs,
                                                       path_tag=self.Tags.OBJDUMP_PATH)
        if use_objdump:
            self.objdump_args = self.defaultObjdumpArgs
        return use_objdump

    def _get_property(self, component_property, _=False, report_usage=False):
        # pylint: disable=no-member
        if report_usage:
            self.set_data_used_for_building(report_usage)
        if component_property == self.ComponentProperty.CODE:
            start = self.elf_info.ie.text_offset
            size = self.elf_info.ie.text_filsz
            return self.file_content[start: start + size]
        if component_property == self.ComponentProperty.DATA:
            start = self.elf_info.ie.data_offset
            size = self.elf_info.ie.data_filsz
            return self.file_content[start: start + size]
        if component_property == self.ComponentProperty.BIN:
            return self.bin_content
        if component_property == self.ComponentProperty.PRIVATE_CODE_BASE_ADDRESS:
            return self.elf_info.private_code_base_address
        if component_property == self.ComponentProperty.UNCOMPRESSED_PRIVATE_CODE_SIZE:
            return self.elf_info.uncompressed_private_code_size
        if component_property == self.ComponentProperty.BSS_SIZE:
            return self.elf_info.bss_size
        if component_property == self.ComponentProperty.TEXT_SIZE:
            return self.elf_info.text_size
        if component_property == self.ComponentProperty.ENTRY_ADDRESS:
            return self.elf_info.entry_address
        if component_property == self.ComponentProperty.DATA_FILSZ:
            return self.elf_info.ie.data_filsz
        if component_property == self.ComponentProperty.DATA_MEMSZ:
            return self.elf_info.ie.data_memsz
        if component_property == self.ComponentProperty.DATA_PADDR:
            return self.elf_info.ie.data_paddr
        if component_property == self.ComponentProperty.DATA_OFFSET:
            return self.elf_info.ie.data_offset
        if component_property == self.ComponentProperty.TEXT_FILSZ:
            return self.elf_info.ie.text_filsz
        if component_property == self.ComponentProperty.TEXT_MEMSZ:
            return self.elf_info.ie.text_memsz
        if component_property == self.ComponentProperty.TEXT_PADDR:
            return self.elf_info.ie.text_paddr
        if component_property == self.ComponentProperty.TEXT_OFFSET:
            return self.elf_info.ie.text_offset
        if component_property == self.ComponentProperty.IMAGE_TEXT_START:
            return self.elf_info.image_text_start
        if component_property == self.ComponentProperty.IMAGE_TEXT_END:
            return self.elf_info.image_text_end
        if component_property == self.ComponentProperty.IMAGE_RAM_START:
            return self.elf_info.image_ram_start
        if component_property == self.ComponentProperty.IMAGE_RAM_END:
            return self.elf_info.image_ram_end
        return None
        # pylint: enable=no-member

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst.objcopy_args = self.objcopy_args
        dst.objdump_args = self.objdump_args
        dst.module_entry = self.module_entry
        dst.markers = dict(self.markers)

    @classmethod
    def _set_property(cls, property_name):
        attr_name = "_" + property_name

        def _lazy_get(self):
            attr = getattr(self, attr_name, None)
            if attr is None:
                self._parse_elf_file()  # pylint: disable=protected-access
            return getattr(self, attr_name)

        setattr(cls, attr_name, None)
        setattr(cls, property_name, property(fget=_lazy_get))
