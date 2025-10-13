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
from lxml.etree import _Comment  # nosec

from .IterableComponent import IterableComponent, IterableEntryComponent
from .GroupComponent import GroupComponent
from .BitRegisterComponent import BitRegisterComponent
from .IComponent import IComponent
from .NumberComponent import NumberComponent
from .StringComponent import StringComponent
from .VersionComponent import VersionComponent
from .ByteArrayComponent import ByteArrayComponent
from .CustomComponent import CustomComponent
from .ElfFileComponent import ElfFileComponent
from .AsymmetricKeyComponent import AsymmetricKeyComponent
from .FileComponent import FileComponent
from .DateComponent import DateComponent
from .BitFieldComponent import BitFieldComponent
from .AesKeyComponent import AesKeyComponent
from .function.HashFunction import HashFunction
from .function.ModulusFunction import ModulusFunction
from .function.SignFunction import SignFunction
from .function.CrcFunction import CrcFunction
from .function.ChecksumFunction import ChecksumFunction
from .function.UpdateManifestFunction import UpdateManifestFunction
from .function.VerifyFunction import VerifyFunction
from .function.CompressedSizeFunction import CompressedSizeFunction
from .function.ExportManifestsFunction import ExportManifestsFunction
from .function.ImportManifestsFunction import ImportManifestsFunction
from .function.ValidateManifestsFunction import ValidateManifestsFunction
from .TableComponent import TableComponent
from .RootComponent import RootComponent
from .DecompositionComponent import DecompositionComponent
from .function.UpdateValueFunction import UpdateValueFunction
from .TableEntryComponent import TableEntryComponent
from ..LibConfig import LibConfig
from ..structures import LibException


class ComponentFactory:
    root = None
    custom_components = {}

    def __init__(self):
        IComponent.componentFactory = self
        self.unknown_types = []
        self._class_map = {'number': NumberComponent,
                           'string': StringComponent,
                           'version': VersionComponent,
                           'byte_array': ByteArrayComponent,
                           'custom_component': CustomComponent,
                           'image': ByteArrayComponent,
                           'configuration': ByteArrayComponent,
                           'layout': ByteArrayComponent,
                           'outputs': ByteArrayComponent,
                           'aliases': ByteArrayComponent,
                           'default': IterableEntryComponent,
                           'entry': IterableEntryComponent,
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
                           IterableComponent.Tags.ITERABLE: IterableComponent,
                           LibConfig.rootTag: RootComponent,
                           'decomposition_plugin': RootComponent,
                           'function_sign': SignFunction,
                           'function_hash': HashFunction,
                           'function_crc': CrcFunction,
                           'function_checksum': ChecksumFunction,
                           'function_verify': VerifyFunction,
                           'function_compressed_size': CompressedSizeFunction,
                           'function_update_value': UpdateValueFunction,
                           'function_export_manifests': ExportManifestsFunction,
                           'function_import_manifests': ImportManifestsFunction,
                           'function_validate_manifests': ValidateManifestsFunction,
                           'function_update_manifest': UpdateManifestFunction,
                           'function_modulus': ModulusFunction,
                           'decomposition': DecompositionComponent,
                           'group': GroupComponent}

    def create_component(self, xml_node, **kwargs):
        if isinstance(xml_node, _Comment):
            return None
        type_name = self._get_type_name(xml_node)
        component = self._class_map[type_name](xml_node, **kwargs)
        if isinstance(component, CustomComponent):
            component = self.custom_components[component.custom_type_name](xml_node, **kwargs)
        return component

    def create_root_component(self, xml_node, skip_calculates: bool = False):
        type_name = self._get_type_name(xml_node)
        component = self._class_map[type_name](xml_node, is_root=True, skip_calculates=skip_calculates)
        return component

    def _get_type_name(self, xml_node):
        type_name = str(xml_node.tag).lower()

        if type_name not in self._class_map:
            if LibConfig.toolType == LibConfig.ToolType.FIT:
                raise LibException(f"Invalid type in xml: {type_name}")
            self.unknown_types.append(type_name)
            type_name = "byte_array"
        return type_name
