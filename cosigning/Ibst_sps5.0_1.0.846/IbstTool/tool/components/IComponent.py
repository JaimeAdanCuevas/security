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
from typing import List
from enum import Enum
from collections import Iterable
from xml.etree import ElementTree as ET

from .IComponentParams import ComponentParams
import re
import os

from ..ExpressionEngine import ExpressionEngine
from ..LibException import ComponentException, LibException, DependencyException
from ..structures import AesEncryption, Buffer
from ..Converter import Converter
from ..utils import align_value
from ..OfflineEncryptionSettings import OfflineEncryptionSettings
from ..LibConfig import LibConfig
from ..dependencies.DependencyFactory import DependencyFactory
from ..dependencies.Dependency import Dependency
from ..utils import parse_json_str
from ..exceptions import JSONException


# TODO: NEED TO BE REFACTORED
class IComponent:
    class ComponentProperty(Enum):
        Value = "value"
        Offset = "offset"
        Size = "size"
        Enabled = "enabled"
        EncryptionMode = "encryption_mode"
        Index = "index"
        BufferSize = "buffer_size"
        InitialVector = "iv"
        InitialVectorSize = "iv_size"
        ChildCount = "child_count"
        ChildCountEn = "child_count_enabled"
        Empty = "empty"
        MapName = "map_name"

    class AlignByte:
        ByteFF = b'\xff'
        Byte00 = b'\0'

    componentFactory = None

    nameTag = "name"
    sizeTag = "size"
    valueTag = "value"
    defaultValueTag = "default_value"
    calculateTag = "calculate"
    alignTag = "align"
    offsetTag = "offset"
    orderTag = "order"
    enabledTag = "enabled"
    encryptTag = "encrypt"
    encryptionModeTag = "encryption_mode"
    dependencyTag = "dependency"
    duplicatesTag = "duplicates"
    paddingTag = "padding"
    fillTag = 'fill'
    offlineEncryptionSettingsTag = 'offline_encryption_settings'
    saveFilePathTag = 'save_file_path'
    ivTag = 'iv'
    calcOnlyTag = "calc_only"
    validateFormulaTag = "validate"
    mapNameTag = "map_name"

    littleOrder = "little"
    bigOrder = "big"
    byte_order = bigOrder

    name = None
    parent = None
    offset = None
    requested_offset = None
    """
    size is the space that the data will eventually take in the binary, after encryption (and possibly others)
    """
    _size = None
    value = None
    value_formula = None
    default_value = None
    size_formula = None
    align_formula = None
    align = None
    enabled_formula = None
    encryption_formula = None
    encryption_key_component = None
    encryption_mode = None
    fill = None
    offline_encryption_settings_path = None
    offline_encryption_settings = None
    loaded_encrypted_data = None
    initial_vector = None
    raw_data = None
    padding_formula = None
    padding = None
    align_byte = None
    save_file_path = None
    iv_source = None
    dependency_formula = None
    duplicates_formula = None
    calc_only = None
    validate_formula = None
    decomp_dependency = None
    map_name = None

    enabled = None
    is_built = False
    error_message = None

    """
    used in table components
    """
    count = None
    index = None
    buffer = None

    """
    GUI section
    """
    optionTypeMap = {"group": "group", "ui_row": "tr", "ui_table": "table"}
    multiLevelComponentsTags = ['bit_register']
    optionTypeTag = 'option_type'
    optionTableTag = optionTypeMap['ui_table']
    optionTrTag = optionTypeMap['ui_row']
    optionTdTag = 'td'
    optionThTag = 'th'
    guiParamsTag = 'ui_params'
    paramsTag = 'params'
    readOnlyTag = 'read_only'
    visibleTag = 'visible'
    labelTag = 'label'
    descriptionTag = 'description'
    actionTag = 'custom_action'
    actionParamsTag = 'action_params'
    groupTag = 'group'
    guiTabTag = 'gui_tab'
    tableColumnsTag = 'columns'
    treeViewTag = 'tree_view'
    typeTag = 'type'
    innerTypeTag = 'inner_type'
    containerTag = 'container'
    pluginTag = 'plugin'
    xmlSaveTag = 'xml_save'
    separatorTag = 'separator'
    regionOptionTag = 'region_option'
    ui_params = None
    params = None
    option_type = None
    label = None
    description = None
    gui_params = None
    columns = None
    component_type = None
    gui_tab = None
    read_only = None
    tree_view = None
    visible = None
    inner_type = None
    node_tag = None
    xml_save_formula = None
    region_option = None

    def __init__(self, xml_node, **kwargs):
        self._init_properties(xml_node, kwargs)
        self._set_parent_child()
        if self._should_omit_parsing(xml_node):
            return
        self._parse_basic_attributes(xml_node)
        self._parse_additional_attributes(xml_node)
        if self.value is not None and self.buffer is None:
            self.parse_string_value(self.value)
        self._parse_gui_attributes(xml_node)
        self.parse_children(xml_node, self.buffer)
        if self.buffer is not None and self.size is None and self.value is None:
            self.size = self.buffer.tell() - self.offset
            self.buffer.seek(-self.size, os.SEEK_CUR)
            self.value = self.buffer.read(self.size)
        self.validate()

    @classmethod
    def is_group(cls, node):
        if node.get(cls.optionTypeTag, None) == cls.optionTypeMap[IComponent.groupTag]:
            return True
        return False

    def update_from_buffer(self, buffer):
        for child in self.children:
            child.update_from_buffer(buffer)

        self.buffer = buffer
        if self.size_formula is not None:
            self.size = self.calculate_value(self.size_formula)
        if self.offset is not None and self.size is not None:
            self._set_value(buffer[self.offset:self.offset + self.size])

    def _parse_gui_attributes(self, xml_node):
        self.params = ComponentParams(self._parse_attribute(xml_node, self.paramsTag, False), self.size)
        self.gui_params = self._parse_attribute(xml_node, self.guiParamsTag, False)
        if self.gui_params is not None:
            self.parse_ui_params()

        self.action = self._parse_attribute(xml_node, self.actionTag, False)
        self.action_params = self._parse_attribute(xml_node, self.actionParamsTag, False)

    def _parse_basic_attributes(self, xml_node):
        self._parse_size(xml_node)
        self._parse_align_tag(xml_node)
        self.requested_offset = self._parse_attribute(xml_node, self.offsetTag, False, None)
        self._parse_value_tag(xml_node)
        self.byte_order = self._parse_attribute(xml_node, self.orderTag, False, self.bigOrder)
        self.value_formula = self._parse_attribute(xml_node, self.calculateTag, False, None)
        self.padding_formula = self._parse_attribute(xml_node, self.paddingTag, False, None)
        self.encryption_formula = self._parse_attribute(xml_node, self.encryptTag, False, None)
        self.offline_encryption_settings_path = self._parse_attribute(xml_node, self.offlineEncryptionSettingsTag,
                                                                      False, None)
        self.iv_source = self._parse_attribute(xml_node, self.ivTag, False, None)
        self.save_file_path = self._parse_attribute(xml_node, self.saveFilePathTag, False, None)
        self.dependency_formula = self._parse_attribute(xml_node, self.dependencyTag, False, None)
        self.duplicates_formula = self._parse_attribute(xml_node, self.duplicatesTag, False, None)
        self.validate_formula = self._parse_attribute(xml_node, self.validateFormulaTag, False, None)
        self.xml_save_formula = self._parse_attribute(xml_node, self.xmlSaveTag, False, None)
        self.fill = self._parse_attribute(xml_node, self.fillTag, False, None)
        self._parse_encryption_tag(xml_node)
        self.map_name = self._parse_attribute(xml_node, self.mapNameTag, False, None)
        
    def _init_properties(self, xml_node, kwargs):
        self.name = self._get_name(xml_node)
        self.label = self._parse_attribute(xml_node, self.labelTag, False, self.name)
        self.node_tag = xml_node.tag
        self._parse_kwargs(kwargs)
        self.children = []
        self.children_by_name = {}
        if self.align_byte is None:
            self.align_byte = LibConfig.defaultPaddingValue
        self.expr_engine = ExpressionEngine(self)
        self.component_type = type(self).__name__
        if self.index is not None:
            self.name += str(self.index)
        self.is_gui = LibConfig.is_gui

    def _parse_align_tag(self, xml_node):
        self.align_formula = self._parse_attribute(xml_node, self.alignTag, False, None)
        if self.buffer is not None and self.align_formula is not None:
            self.align = self.calculate_value(self.align_formula)
            if self.align > self.buffer.max_size:
                raise ComponentException("Alignment of component {} exceed buffer size", self.name)

            if self.align != 0 and (self.buffer.tell() % self.align) != 0:
                difference = self.align - (self.buffer.tell() % self.align)
                self.offset = self.buffer.tell() + difference
                self.buffer.seek(self.offset)

    def _parse_size(self, xml_node):
        if self.sizeTag in xml_node.attrib:
            self.size_formula = xml_node.attrib[self.sizeTag]
            value = self.calculate_value(formula=self.size_formula, allow_calculate=True)
            self.size = value

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    def _parse_value_tag(self, xml_node):
        if self.valueTag in xml_node.attrib:
            self.value = xml_node.attrib[self.valueTag]
        elif self.buffer is not None:
            if not self.requested_offset:
                self.offset = self.buffer.tell()
            else:
                self.offset = self.calculate_value(self.requested_offset)
            if self.offset < self.buffer.tell():
                raise ComponentException(f"Requested offset {self.requested_offset} is smaller than current offset {self.buffer.tell()}")
            self.buffer.seek(self.offset)
            if self.sizeTag in xml_node.attrib:
                if self.buffer.max_size < self.offset + self.size:
                    raise ComponentException(f"Buffer size too small, failed to read at offset {self.offset}")
                self.value = self.buffer.read(self.size)

    def _parse_encryption_tag(self, xml_node):
        if self.encryptionModeTag in xml_node.attrib:
            try:
                self.encryption_mode = AesEncryption.parse_mode(xml_node.attrib[self.encryptionModeTag])
            except LibException as e:
                raise ComponentException(str(e), self.name)

    def _set_parent_child(self):
        if self.parent is not None:
            self.parent.children.append(self)
            if self.name not in self.parent.children_by_name:
                self.parent.children_by_name[self.name] = self

    def _parse_kwargs(self, kwargs):
        self.buffer = kwargs.get('buffer')
        self.index = kwargs.get('index')
        self.parent = kwargs.get('parent')
        if self.componentFactory:
            is_root = kwargs.get("is_root", False)
            if is_root:
                self.componentFactory.root = self
            self.rootComponent = self.componentFactory.root

    def _should_omit_parsing(self, xml_node):
        self.calc_only = self._parse_attribute(xml_node, self.calcOnlyTag, False, None)
        self.enabled_formula = self._parse_attribute(xml_node, self.enabledTag, False, None)
        try:
            if not self._is_enabled() and not self.calc_only == "true":
                return True
        except(ValueError, ComponentException, LibException):
            # this error may occur because of non-initialized fields that enabled formula may refer to,
            # so it shoud not be thrown. If we cannot determine if component is disabled, we cannot resign from parsing it
            self.enabled = None
        return False

    def is_setting(self):
        if self.parent and self.parent.node_tag == LibConfig.settingsTag:
            return True
        if self.parent:
            return self.parent.is_setting()
        return False

    @classmethod
    def get_name(cls, xml_node):
        if cls.nameTag in xml_node.attrib:
            return xml_node.attrib[cls.nameTag]
        return xml_node.tag

    def _get_name(self, xml_node):
        return self.get_name(xml_node)

    def validate(self):
        if " " in self.name:
            raise ComponentException("Object's name cannot contain space",
                                     self.name)

        if self.encryption_formula and not self.encryption_mode:
            raise ComponentException("'{}' is required when '{}' attribute was specified".
                                     format(self.encryptionModeTag, self.encryptTag), self.name)

        if self.align_formula and self.requested_offset:
            raise ComponentException("You can use only one at a time: {} or {}".format(self.offsetTag, self.alignTag),
                                     self.name)

    def validate_value(self):
        if not self.value:
            raise ComponentException("File name is not specified, use 'value' attribute", self.name)

    def _parse_additional_attributes(self, xml_node):
        pass

    def _parse_string_value(self, value):
        if not value:
            raise ComponentException("Value cannot be empty", self.name)
        return Converter.string_to_int(value)

    def parse_string_value(self, value):
        old_val = self.value
        self._set_value(self._parse_string_value(value))
        return [self] if old_val != self.value else []

    def parse_children(self, xml_node, buffer=None):
        if not xml_node:
            return
        try:
            for child_node in xml_node:
                self.componentFactory.create_component(child_node, buffer=buffer, parent=self)
        except ComponentException as ex:
            self.trace_exception(ex)

    def _set_value(self, value):
        self.value = value

    def trace_exception(self, exception):
        if isinstance(exception, ComponentException):
            exception.trace.append(self.name)
        raise exception

    def __str__(self):
        return self.name

    def len(self):
        if self.size is not None:
            return self.size

        raise ComponentException("Size is unknown - object's layout hasn't been built yet",
                                 self.name)

    def get_property(self, property_name, allow_calculate=False):
        self._check_error()
        property_name, index_from, index_to = self.parse_property_indexing(property_name)
        component_property = self.parse_property_name(property_name)

        value = self._get_property(component_property, allow_calculate)

        if value is None:
            raise ComponentException("Missing handler for property: '{}'".format(property_name), self.name)

        if index_from is None and index_to is None:
            return value

        if not isinstance(value, Iterable):
            raise ComponentException("'{}' cannot be accessed by index"
                                     .format(property_name), self.name)

        return self.get_value_from_index(value, index_from, index_to)

    def _get_property(self, component_property, allow_calculate=False):
        if component_property == self.ComponentProperty.Value:
            if self.value is not None:
                return self.value
            if self.has_dependencies():
                return None  # value is none, so it means that dependency hasn't been resolved yet
            if self.value_formula and allow_calculate:
                return self.calculate_value(formula=self.value_formula, allow_calculate=allow_calculate)
            return self.get_default_value()
        elif component_property == self.ComponentProperty.Size:
            return self.size
        elif component_property == self.ComponentProperty.Offset:
            return self.offset
        elif component_property == self.ComponentProperty.Enabled:
            return self._is_enabled()
        elif component_property == self.ComponentProperty.Index:
            return self.get_table_index()
        elif component_property == self.ComponentProperty.MapName:
            if "/" in self.map_name:
                try:
                    calculated_val = self.calculate_value(formula=self.map_name, allow_calculate=allow_calculate)
                    return calculated_val
                except ComponentException:
                    return self.map_name
            else:
                return self.map_name

        if component_property == self.ComponentProperty.EncryptionMode:
            return AesEncryption.ModeTypes[self.encryption_mode]
        if component_property == self.ComponentProperty.BufferSize:
            if self.buffer is None:
                raise ComponentException("Decomposition buffer not set properly.")
            else:
                return self.buffer.max_size
        if component_property == self.ComponentProperty.InitialVector:
            if not self.initial_vector:
                raise ComponentException("This component doesn't have initialisation vector for AES encryption",
                                         self.name)
            return self.initial_vector
        if component_property == self.ComponentProperty.InitialVectorSize:
            if not self.initial_vector:
                raise ComponentException("This component doesn't have initialisation vector for AES encryption",
                                         self.name)
            return len(self.initial_vector)
        if component_property == self.ComponentProperty.ChildCount:
            return len(self.children)
        if component_property == self.ComponentProperty.ChildCountEn:
            enabled_children = [child for child in self.children if child._is_enabled()]
            return len(enabled_children)
        if component_property == self.ComponentProperty.Empty:
            return self._is_empty()

    def parse_property_name(self, property_name):
        try:
            return self._get_component_property(property_name)
        except Exception:
            values = [item.value for item in self.ComponentProperty]
            raise ComponentException("No such property: '{}', use one of:\n   {}".
                                     format(property_name, ", ".join(values)), self.name)

            # Overridden, if dynamic enum is needed

    def _get_component_property(self, property_name):
        return self.ComponentProperty(property_name)

    @staticmethod
    def parse_property_indexing(property_name):
        match = re.match("(.+)\\[((?:0x)?.+):((?:0x)?.+)\\]", property_name)
        if match:
            property_name = match.group(1)
            index_from = match.group(2)
            index_to = match.group(3)
        else:
            index_from = None
            index_to = None

        return property_name, index_from, index_to

    @staticmethod
    def get_value_from_index(value, index_from, index_to):
        index_from = Converter.string_to_int(index_from)
        index_to = Converter.string_to_int(index_to)

        if index_from > index_to:
            value = bytes(reversed(value))
            index_from = len(value) - index_from
            index_to = len(value) - index_to

        return value[index_from:index_to]

    def get_bytes(self):
        self._check_error()
        if self.value is None:
            raise ComponentException("You can only get bytes from objects with defined value",
                                     self.name)
        if self.is_offline_encryption_load():
            # We expect here that encrypted data was already loaded from file as a 'bytes' and is of proper size
            return self.value
        try:
            value = self._get_bytes()
            if self.byte_order == self.littleOrder:
                value = bytearray(value)
                value.reverse()
            return bytes(self._align_bytes_to_size(value))
        except (LibException, ValueError, TypeError, OverflowError) as ex:
            raise ComponentException("Failed to get bytes from value of type '{}', error: {}"
                                     .format(type(self.value).__name__, str(ex)), self.name)

    def _get_bytes(self):
        raise ComponentException("Cannot get bytes from object of type '{}'"
                                 .format(type(self).__name__), self.name)

    def _align_bytes_to_size(self, value):
        value = bytearray(value)
        delta_length = self.size - len(value)
        if delta_length > 0:
            value.extend(self.align_byte * delta_length)
        elif delta_length < 0:
            raise ComponentException("Provided value is too big ({} bytes), maximum size is {} bytes"
                                     .format(len(value), self.size), self.name)
        return value

    def _is_enabled(self):
        if self.enabled_formula:
            try:
                self.enabled = self._parse_enabled()
            except(ValueError, ComponentException, LibException) as e:
                self.enabled = None
                self.trace_exception(e)
        else:
            self.enabled = True
        return self.enabled

    def _parse_enabled(self):
        enabled = self.calculate_value(formula=self.enabled_formula, allow_calculate=True)
        if not isinstance(enabled, bool):
            raise ComponentException("Invalid formula for '{}' - result is not bool: {}".
                                     format(self.enabledTag, self.enabled_formula), self.name)
        return enabled

    def _is_empty(self):
        raise ComponentException("Cannot check if object of type '{}' is empty"
                                 .format(type(self).__name__), self.name)

    def load_offline_encryption_settings(self):
        if self.offline_encryption_settings_path is None:
            return
        settings_node = self.calculate_value(formula=self.offline_encryption_settings_path)
        try:
            self.offline_encryption_settings = OfflineEncryptionSettings(settings_node)
        except LibException as e:
            raise ComponentException("Failed to load offline encryption settings, reason: {}".format(str(e)), self.name)

    def is_offline_encryption(self):
        if self.offline_encryption_settings is None:
            return False
        return self.offline_encryption_settings.enabled

    def is_offline_encryption_load(self):
        return self.is_offline_encryption() and self.offline_encryption_settings.load_phase

    def is_offline_encryption_save(self):
        return self.is_offline_encryption() and not self.offline_encryption_settings.load_phase

    def handle_offline_encryption_load(self):
        store_dir = self.offline_encryption_settings.store_dir
        if not store_dir:
            raise ComponentException('{} must not be empty'.format(OfflineEncryptionSettings.Tags.storeDir))
        file_names = self.offline_encryption_settings.get_files_names(self.name)
        # Load encrypted data
        encrypted_path = os.path.join(store_dir, file_names.encrypted)
        if not os.path.isfile(encrypted_path):
            raise ComponentException("{} is missing - it should contain encrypted data".format(encrypted_path),
                                     self.name)
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        # Load unencrypted data - just to verify that it differs from those encrypted
        unencrypted_path = os.path.join(store_dir, file_names.unencrypted)
        if not os.path.isfile(unencrypted_path):
            raise ComponentException("{} is missing - it's used to check if data is encrypted "
                                     "(it must differ from encrypted data)".format(unencrypted_path), self.name)
        with open(unencrypted_path, 'rb') as f:
            unencrypted_data = f.read()
        # Compare data
        if unencrypted_data == encrypted_data:
            raise ComponentException("It seems that data were not encrypted:\n{}\nis the same as:\n{}".
                                     format(unencrypted_path, encrypted_path), self.name)
        self.loaded_encrypted_data = encrypted_data
        self.size = len(self.loaded_encrypted_data)
        # Load initialisation vector
        iv_path = os.path.join(store_dir, file_names.iv)
        if not os.path.isfile(iv_path):
            raise ComponentException("{} is missing - it should contain initialisation vector (can be filled with 0xFF "
                                     "if used encryption mode doesn't use initialisation vector)"
                                     .format(iv_path),
                                     self.name)
        with open(iv_path, 'rb') as f:
            self.initial_vector = f.read()
        if len(self.initial_vector) != AesEncryption.AesBlockSizeBytes:
            raise ComponentException("Length of initialisation vector is {} but should be {}".
                                     format(len(self.initial_vector), AesEncryption.AesBlockSizeBytes), self.name)

    def handle_offline_encryption_save(self):
        store_dir = self.offline_encryption_settings.store_dir
        if not store_dir:
            raise ComponentException('{} must not be empty'.format(OfflineEncryptionSettings.Tags.storeDir))
        if os.path.isfile(store_dir):
            raise ComponentException("Cannot store data to encrypt in: {}, it's a file.".format(store_dir), self.name)
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)
        file_names = self.offline_encryption_settings.get_files_names(self.name)
        unencrypted_path = os.path.join(store_dir, file_names.unencrypted)
        with open(unencrypted_path, 'wb') as f:
            f.write(self.get_bytes())
        if self.initial_vector is not None:
            iv_path = os.path.join(store_dir, file_names.iv)
            with open(iv_path, 'wb') as f:
                f.write(self.initial_vector)

    def build_layout(self, buffer, clear_build_settings=False):
        if clear_build_settings:
            self.is_built = False

        self.offset = buffer.tell()

        if not self._is_enabled() and not self.calc_only:
            self.size = 0
            if self.value is None:
                self._set_value(self.get_default_value())
            return

        self._check_error()

        if self.align_formula:
            self.align = self.calculate_value(self.align_formula)
            if self.align != 0:
                self.offset = align_value(self.offset, self.align)
                buffer.seek(self.offset)

        if self.requested_offset:
            self.offset = self.calculate_value(self.requested_offset)
            if self.offset < buffer.tell():
                raise ComponentException("Cannot set requested offset: {}, current offset is already: {}".
                                         format(hex(self.offset), hex(buffer.tell())), self.name)
            buffer.seek(self.offset)

        self._build_layout()
        if self.calc_only:
            return

        if self.value is not None:
            buffer.write(self.get_bytes())
        elif self.children is not None:
            for child in self.children:
                try:
                    child.build_layout(buffer, clear_build_settings)
                except ComponentException as ex:
                    self.trace_exception(ex)
        elif self.size is None:
            raise ComponentException("Size is unknown", self.name)

        # size might be not specified for some type of values or if there are children
        if self.size is None:
            self.size = buffer.tell() - self.offset

        self._add_padding(buffer)

        self.load_offline_encryption_settings()
        if self.is_offline_encryption():
            if self.is_offline_encryption_save() and self.encryption_mode is not None:
                self.initial_vector = AesEncryption.create_initialisation_vector(self.encryption_mode)
            elif self.is_offline_encryption_load():
                self.handle_offline_encryption_load()
        elif self.encryption_formula is not None:
            # encryption might influence the size
            try:
                self.encryption_key_component = self.calculate_value_from_path(self.encryption_formula)
                if self.encryption_key_component._is_enabled():
                    initial_vector = None
                    if self.iv_source is not None:
                        initial_vector = self.calculate_value(self.iv_source)
                    if not initial_vector:
                        self.initial_vector = AesEncryption.create_initialisation_vector(self.encryption_mode)
                    else:
                        self.initial_vector = initial_vector
                    # encryption might increase the size of the component
                    self.size = self.encryption_key_component.get_encrypted_data_size(self.size,
                                                                                      self.encryption_mode)
                else:
                    self.initial_vector = AesEncryption.get_empty_initialisation_vector(self.encryption_mode)
                    self.encryption_key_component = None
            except LibException as e:
                raise ComponentException("Encryption failed: {}".format(str(e)), self.name)

        buffer.seek(self.offset + self.size)

    def _build_layout(self):
        if self.value_formula and not self.size:
            try:
                self.size = len(self.calculate_value(formula=self.value_formula))
            except (TypeError, AttributeError) as ex:
                raise ComponentException("Cannot get size from the result of the formula '{}' because: {}"
                                         .format(self.value_formula, ex), self.name)

        if self.value_formula and self.value is None:
            # Use default value as a temporary value
            # - proper value will be calculated at a later stage
            self._set_value(self.get_default_value())

    def check_validate_formula(self):
        if self.validate_formula:
            if not self.calculate_value(self.validate_formula, True):
                raise ComponentException(self.name, f'\nValidation formula failed:\n  {self.validate_formula}')

    def build(self, buffer):
        if (not self._is_enabled() and not self.calc_only) or self.is_built:
            return

        self._check_error()

        self._build(buffer)
        self.check_validate_formula()
        if self.calc_only:
            return

        self.validate_file_size()

        if self.offset is not None:
            buffer.seek(self.offset)
            if self.fill is not None:
                fill = self.calculate_value(self.fill, True)
                try:
                    fill_arr = fill.to_bytes(1, self.byte_order)
                except OverflowError:
                    raise ComponentException(self.name, f"Fill value: {self.fill} is longer than 1 byte")
                buffer.write(fill_arr * self.size)
                buffer.seek(self.offset)
        if self.value is not None:
            if self.offset is not None:
                buffer.write(self.get_bytes())
            self._fill_padding(buffer)
        else:
            for child in self.children:
                try:
                    child.build(buffer)
                except ComponentException as ex:
                    self.trace_exception(ex)

            self._fill_padding(buffer)

            if self.offset is not None:
                buffer.seek(self.offset)
                self._set_value(buffer.read(self.size))

        if self.is_offline_encryption():
            if self.is_offline_encryption_save():
                self.handle_offline_encryption_save()
                buffer.seek(self.offset)
                buffer.write(bytes([0xFF] * self.size))
            elif self.is_offline_encryption_load():
                self.raw_data = self.value
                self.value = self.loaded_encrypted_data
                buffer.seek(self.offset)
                buffer.write(self.loaded_encrypted_data)
        else:
            try:
                if self.encryption_key_component:
                    self.raw_data = self.value
                    self._set_value(
                        self.encryption_key_component.encrypt(self.value, self.encryption_mode, self.initial_vector))
                    buffer.seek(self.offset)
                    buffer.write(self.value)
            except Exception as e:
                raise ComponentException("Failed to encrypt: {}".format(str(e)), self.name)

        if self.offset is not None:
            # Let's also validate if we've written the proper number of bytes into the buffer
            size_in_buffer = buffer.tell() - self.offset
            if size_in_buffer != self.size:
                raise ComponentException("Invalid final size of the component, expected: {} but is {}".
                                         format(self.size, size_in_buffer), self.name)

        self.is_built = True

        if self.save_file_path is not None:
            path = self.calculate_value(self.save_file_path)
            if path:
                with open(path, 'wb') as f:
                    f.write(self.get_bytes())
                print("Content of {} saved to {}\n".format(self.get_string_path(), path))

    def _build(self, _):
        if self.value_formula:
            self._set_value(self.calculate_value(formula=self.value_formula))

    def validate_file_size(self):
        pass

    def _add_padding(self, buffer):
        if self.padding_formula is not None:
            padding_value = self.calculate_value(self.padding_formula, allow_calculate=True)
            if not isinstance(padding_value, int):
                raise ComponentException("Padding formula must result in an integer, but is {}".
                                         format(type(padding_value).__name__), self.name)
            new_size = align_value(self.size, padding_value)
            self.padding = bytes([0] * (new_size - self.size))
            self.size = new_size
            buffer.seek(self.offset + self.size)

    def _fill_padding(self, buffer):
        if not self.padding:
            return

        buffer.seek(self.offset + self.size - len(self.padding))
        buffer.write(self.padding)

    def get_child(self, child_name):
        return self._get_child(child_name)

    def __getitem__(self, index):
        if isinstance(index, str):
            return self.get_child(index)
        if isinstance(index, int):
            return self.children[index]
        raise ComponentException(f"Cannot use '{type(index).__name__}' as component index", self.name)

    def _get_child(self, child_name):
        if self.children_by_name is None:
            raise ComponentException("'{}' has no children".
                                     format(self.name), self.name)
        if child_name in self.children_by_name:
            return self.children_by_name[child_name]
        # search among transparent gui nodes (optionTypeMap) and bit_registers (multiLevelComponentsTags)
        gui_children = filter(lambda child: child.node_tag in self.optionTypeMap or child.node_tag in self.multiLevelComponentsTags, self.children)
        for gui_node in gui_children:
            try:
                return gui_node.get_child(child_name)
            except ComponentException:
                pass
        raise ComponentException(
            f"No '{child_name}' child. Choose one of: {', '.join(self.children_by_name.keys())}",
            self.name)

    def remove_child(self, child_name):
        if child_name in self.children_by_name:
            child_to_remove = self.children_by_name[child_name]
            self.children.remove(child_to_remove)
            self.children_by_name.pop(child_name)

    def _write_bytes(self, comp_bytes, buffer, offset=None):
        if offset is not None:
            if buffer.max_size <= offset:
                raise ComponentException(
                    "Component has offset ({}) higher than binary size ({})!".format(offset, buffer.max_size),
                    self.name)
        else:
            offset = buffer.tell()
        if buffer.max_size < offset + len(comp_bytes):
            raise ComponentException(
                "Component exceeded the binary size\n"
                "Offset: {} Size: {}\n"
                "Maximum binary size: {}".format(offset, len(comp_bytes), buffer.max_size),
                self.name)

        buffer.seek(offset)
        buffer.write(comp_bytes)

    def calculate_value(self, formula, allow_calculate=False):
        return self.expr_engine.calculate_value(formula, None, allow_calculate)

    def calculate_value_from_path(self, path, allow_calculate=False):
        return self.expr_engine.calculate_value_from_path(path, allow_calculate)

    def get_dependencies(self, duplicates: bool = False) -> List[Dependency]:
        if not duplicates and self.read_only is None:
            self.read_only = True
        try:
            formula = self.duplicates_formula if duplicates else self.dependency_formula
            json_dic = parse_json_str(formula)
        except JSONException:
            raise ComponentException(f"Wrong json syntax: {formula}", self.name)

        try:
            return [DependencyFactory.create_dependency(dependency_type, properties, self, duplicates)
                    for el in json_dic for dependency_type, properties in el.items()]
        except DependencyException as e:
            raise ComponentException(str(e), self.name)

    def has_dependencies(self):
        return bool(self.dependency_formula)

    def has_duplicates(self):
        return bool(self.duplicates_formula)

    def to_xml_node(self, parent, create_groups: bool = False):
        if not self.is_setting_saveable:
            return
        if self.xml_save_formula and not self.calculate_value(self.xml_save_formula):
            return
        # TODO: FIT xml serializing: should be moved
        is_gui_node = self.node_tag in self.optionTypeMap
        node = parent
        if create_groups or not is_gui_node:
            node_name = 'setting'
            if is_gui_node:
                node_name = self.node_tag
            node = ET.SubElement(parent, node_name, {self.nameTag: self.name})
            node.set(self.valueTag, self.get_value_string())
            if is_gui_node and not self.children_by_name:
                parent.remove(node)
        if self.children_by_name:
            for child in self.children_by_name.values():
                child.to_xml_node(node, create_groups)

    def _raise_missing_child(self, childTag):
        raise ComponentException("Missing mandatory child tag: '{}'".format(childTag),
                                 self.name)

    # This is used for lazy error checking. Eg.: certain types (used in settings section) try to load files
    # but they may not be needed at all. So it's convenient to set the error message when we fail to initialise
    # but only return error to user if we try to use this node.
    def _check_error(self):
        if self.error_message is not None and not self.is_gui:
            raise ComponentException(self.error_message, self.name)

    def get_value_string(self):
        return self._get_val_string(self.value)

    def get_default_value_string(self):
        return self._get_val_string(self.default_value)

    def _get_val_string(self, val):
        return None if val is None else str(val)

    def get_string_path(self):
        return "{}/{}".format(self.parent.get_string_path() if self.parent else "", self.name)

    def get_table_index(self):
        if self.index is not None:
            return self.index
        if self.parent is not None:
            return self.parent.get_table_index()
        return None

    def get_parent_table_index(self):
        if self.index is not None and self.parent is not None:
            return self.parent.get_table_index()
        if self.parent is not None:
            return self.parent.get_parent_table_index()
        return None

    def _parse_node(self, xml_node, tag):
        node = xml_node.find(tag)
        if node is None:
            raise ComponentException("Cannot find required node %s" % tag, self.name)
        return node

    def _parse_attribute(self, xml_node, tag, required=True, default=None):
        if tag not in xml_node.attrib and required:
            raise ComponentException("Cannot find required attribute %s" % tag, self.name)
        if tag in xml_node.attrib:
            return xml_node.attrib[tag]
        return default

    # GUI section

    """
    parse ui_params which should be provided as JSON in format {'a':'b', 'c':'d'}
    """

    def parse_ui_params(self):
        try:
            ui_dict = parse_json_str(self.gui_params)
        except JSONException as ex:
            raise ComponentException("Cannot parse ui_params '{}' because: {}"
                                     .format(self.gui_params, ex), self.name)

        ui_params_map = {self.readOnlyTag: (self.readOnlyTag, Converter.string_to_bool),
                         self.visibleTag: (self.visibleTag, Converter.string_to_bool),
                         self.optionTypeTag: (self.optionTypeTag, lambda value: value),
                         self.descriptionTag: (self.descriptionTag, lambda value: value),
                         self.innerTypeTag: (self.innerTypeTag, lambda value: value),
                         self.guiTabTag: (self.guiTabTag, lambda value: value),
                         self.treeViewTag: (self.treeViewTag, Converter.string_to_bool),
                         self.regionOptionTag: (self.regionOptionTag, lambda value: value)}

        for key, (field_name, convert_function) in ui_params_map.items():
            if key in ui_dict:
                setattr(self, field_name, convert_function(ui_dict[key]))

    def get_all_children(self, children: dict):
        for child in self.descendants:
            if child.name in children:
                raise ComponentException(f"There already exists child with the name '{child.name}':"
                                         f" {child.get_string_path()}")
            children[child.name] = child

    def get_children_with_tag(self, tag) -> ["IComponent"]:
        if self.children:
            return [child for child in self.children if child.node_tag == tag]
        return []

    @property
    def descendants(self):
        for child in self.children:
            yield child
            for descendant in child.descendants:
                yield descendant

    def copy_to(self, dst):
        if type(self) != type(dst):
            raise ComponentException(
                f"Source and destination components need to have the same type. type({self.name}) != type({dst.name})")
        self._copy_to(dst)

    def _copy_to(self, dst):
        """Copies defined attributes from self to destination object.
        Copying of component specific attributes is that component responsibility."""
        dst.value = self.value
        dst.size = self.size

    @property
    def is_setting_saveable(self):
        if self.has_dependencies():
            try:
                json_dep_list = parse_json_str(self.dependency_formula)
            except JSONException as ex:
                raise ComponentException(f"Wrong json syntax: {self.dependency_formula}", self.name)
            for dep in json_dep_list:
                if Dependency.Tags.getTag in dep or Dependency.Tags.switchTag in dep:
                    return False
        if self.value_formula is not None:
            return False
        if self.read_only:
            return False
        return True

    @staticmethod
    def is_node_overridable(sett: ET.Element):
        read_only = None
        if IComponent.guiParamsTag in sett.attrib.keys():
            try:
                ui_params_dict = parse_json_str(sett.attrib[IComponent.guiParamsTag])
            except JSONException as ex:
                raise ComponentException("Cannot parse ui_params '{}' because: {}"
                                         .format(sett.attrib[IComponent.guiParamsTag], ex), sett.tag)

            if IComponent.readOnlyTag in ui_params_dict:
                read_only = Converter.string_to_bool(ui_params_dict[IComponent.readOnlyTag])
                if read_only:
                    return False
        if IComponent.dependencyTag in sett.attrib.keys() and read_only is not False:
            return False
        if IComponent.calculateTag in sett.attrib.keys():
            return False
        if IComponent.separatorTag == sett.tag:
            return False
        return True

    def add_decomp_dependency(self, sett):
        self.decomp_dependency.append(sett)

    def _update_decomp_dependency(self):
        from mmap import ACCESS_READ
        with open(self.value, 'rb') as file:
            with Buffer(file.fileno(), 0, access=ACCESS_READ) as buffer:
                for dep in self.decomp_dependency:
                    dep.update_from_buffer(buffer)

    def initialize_defaults(self):
        if self.node_tag not in self.optionTypeMap:
            if self.value is not None:
                self.default_value = self.value
            elif self.value_formula:
                try:
                    self.default_value = self.calculate_value(self.value_formula, False)
                # todo some cases like using external container dependency rise different exception
                except Exception:
                    self.default_value = None
        for child in self.children:
            child.initialize_defaults()

    def get_default_value(self):
        if self.default_value:
            return self.default_value
        if self.has_dependencies():
            switch_dependency = [dependency for dependency in self.get_dependencies()
                                 if dependency.tag == Dependency.Tags.switchTag]

            if switch_dependency:
                depend = switch_dependency[0]
                configuration_component = self.rootComponent.get_child(LibConfig.settingsTag)
                reference_setting = configuration_component.get_child(depend.referenced_set_name)
                depend.set_referenced_setting(reference_setting)
                depend.set_default_value()
                return self.default_value
        return 0

    def is_default(self):
        return bool(self.value == self.get_default_value())

    @property
    def map_data(self) -> ([int, int, int, str]):
        """Returns list of start offset, length, intent, area name"""
        data = []
        intent = 0
        map_name = self.get_property("map_name", True) if self.map_name and self.size and self.offset is not None else None
        if map_name:
            data.append((self.offset, self.size, 0, map_name))
            intent = 1
        for child in self.children:
            if child.map_data:
                leveled = ((x[0], x[1], x[2] + intent, x[3]) for x in child.map_data)
                data.extend(leveled)
        return data

    def set_map_names_for_layout(self):
        if not self.map_name:
            self.map_name = self.label if self.label else self.name
        child: IComponent
        for child in self.children:
            child.set_map_names_for_layout()

    def clear_data(self):
        self._clear_data()
        for child in self.children:
            child.clear_data()

    def _clear_data(self):
        pass
