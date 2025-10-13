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

from .BitRegisterComponent import BitRegisterComponent
from .IComponent import IComponent
from .NumberComponent import NumberComponent
from .StringComponent import StringComponent
from .VersionComponent import VersionComponent
from .ByteArrayComponent import ByteArrayComponent
from .ElfFileComponent import ElfFileComponent
from .AsymmetricKeyComponent import AsymmetricKeyComponent
from .FileComponent import FileComponent
from .DateComponent import DateComponent
from .BitFieldComponent import BitFieldComponent
from .AesKeyComponent import AesKeyComponent
from .function.HashFunction import HashFunction
from .function.SignFunction import SignFunction
from .function.CrcFunction import CrcFunction
from .function.ChecksumFunction import ChecksumFunction
from .function.VerifyFunction import VerifyFunction
from .function.CompressedSizeFunction import CompressedSizeFunction
from .function.IccProfileFunction import IccProfileFunction
from .TableComponent import TableComponent
from .RootComponent import RootComponent
from .HashComponent import HashComponent
from .DecompositionComponent import DecompositionComponent
from .function.UpdateValueFunction import UpdateValueFunction
from .TableEntryComponent import TableEntryComponent
from ..LibConfig import LibConfig


class ComponentFactory(object):
    root = None

    def __init__(self):
        IComponent.componentFactory = self
        self.unknown_types = []
        self._class_map = {'number': NumberComponent,
                           'string': StringComponent,
                           'version': VersionComponent,
                           'byte_array': ByteArrayComponent,
                           'elf_file': ElfFileComponent,
                           'rsa_key': AsymmetricKeyComponent,
                           'asymmetric_key': AsymmetricKeyComponent,
                           'aes_key': AesKeyComponent,
                           'file': FileComponent,
                           'date': DateComponent,
                           'bit_field': BitFieldComponent,
                           'bit_register': BitRegisterComponent,
                           'table': TableComponent,
                           'table_entry_pointer': TableEntryComponent,
                           LibConfig.rootTag: RootComponent,
                           'hash': HashComponent,
                           'function_sign': SignFunction,
                           'function_hash': HashFunction,
                           'function_crc': CrcFunction,
                           'function_checksum': ChecksumFunction,
                           'function_verify': VerifyFunction,
                           'function_compressed_size': CompressedSizeFunction,
                           'function_update_value': UpdateValueFunction,
                           'function_icc_profile': IccProfileFunction,
                           'decomposition': DecompositionComponent}

    def create_component(self, xml_node, **kwargs):
        type_name = self._get_type_name(xml_node)
        component = self._class_map[type_name](xml_node, **kwargs)
        return component

    def create_root_component(self, xml_node):
        type_name = self._get_type_name(xml_node)
        component = self._class_map[type_name](xml_node, is_root=True)
        return component

    def _get_type_name(self, xml_node):
        type_name = xml_node.tag.lower()

        if type_name not in self._class_map:
            self.unknown_types.append(type_name)
            type_name = "byte_array"
        return type_name
