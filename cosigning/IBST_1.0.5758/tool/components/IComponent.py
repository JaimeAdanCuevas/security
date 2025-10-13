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
import re
import os
from collections import namedtuple
from mmap import ACCESS_READ
from copy import copy

from typing import List, Optional, Iterable, Tuple, Dict, Generator
from enum import Enum
from lxml.etree import SubElement  # nosec - only used to create xml objects (nodes)

from .IComponentParams import ComponentParams
from ..AttributeGroup import DecompositionAttributes, UiParams
from ..CustomError import CustomError, Severity
from ..ExpressionEngine import ExpressionEngine
from ..FileOpener import open_file
from ..FileManager import FileManager
from ..LibException import ComponentException, LibException, DependencyException, ValidateException, JSONException, \
    ValueException
from ..PropertyState import PropertyState, ComponentPreChangeState
from ..structures import AesEncryption, Buffer
from ..Converter import Converter
from ..utils import align_value, MapData
from ..OfflineEncryptionSettings import OfflineEncryptionSettings
from ..LibConfig import LibConfig
from ..dependencies.DependencyFactory import DependencyFactory
from ..dependencies.Dependency import Dependency
from ..utils import parse_json_str


class IComponent:
    class ComponentProperty(Enum):
        VALUE = "value"
        OFFSET = "offset"
        SIZE = "size"
        ENABLED = "enabled"
        ENCRYPTION_MODE = "encryption_mode"
        INDEX = "index"
        BUFFER_SIZE = "buffer_size"
        INITIAL_VECTOR = "iv"
        INITIAL_VECTOR_SIZE = "iv_size"
        CHILD_COUNT = "child_count"
        CHILD_COUNT_ENABLED = "child_count_enabled"
        EMPTY = "empty"
        MAP_NAME = "map_name"
        LEGACY_MAP_NAME = "legacy_map_name"
        VISIBLE = "visible"
        READ_ONLY = "read_only"
        VALUE_LIST = "value_list"
        DEFAULT_VALUE = 'default_value'
        IS_DEFAULT = 'is_default'

    class AlignByte:
        ByteFF = b'\xff'
        Byte00 = b'\0'

    class CustomActionDefinition:
        """
        Model for custom action definition for components.
        """

        class Tags:
            NAME = "name"
            ARGUMENTS = "arguments"

        def __init__(self, name: str, arguments=None):
            self.name: str = name
            self.arguments: List = arguments if arguments is not None else []

        @classmethod
        def from_action_dict(cls, action: Dict):
            name = action.get(cls.Tags.NAME)
            arguments = action.get(cls.Tags.ARGUMENTS)

            return cls(name, arguments)

    componentFactory = None

    class Tags:
        NAME = "name"
        SIZE = "size"
        VALUE = 'value'
        CHILDREN = "children"
        CALCULATE = 'calculate'
        DECOMPOSITION_CALCULATE = "decomposition_calculate"
        ALIGN = "align"
        ALIGN_WITH_END = "align_with_end"
        OFFSET = "offset"
        ORDER = "order"
        ENABLED = "enabled"
        ENCRYPT = "encrypt"
        ENCRYPTION_MODE = "encryption_mode"
        DEPENDENCY = "dependency"
        DUPLICATES = "duplicates"
        PADDING = "padding"
        FILL = "fill"
        ALIGN_BYTE = "align_byte"
        OFFLINE_ENCRYPTION_SETTINGS = "offline_encryption_settings"
        SAVE_FILE_PATH = "save_file_path"
        IV = "iv"
        CALC_ONLY = "calc_only"
        VALIDATE_FORMULA = "validate"
        MAP_NAME = "map_name"
        LEGACY_MAP_NAME = "legacy_map_name"
        LEGACY = "legacy"
        ITERABLE_DESCENDANT = "iterable_descendant"
        INDEX = "index"
        CUSTOM_ACTIONS = "custom_actions"
        MULTI_LEVEL_COMPONENTS = ['bit_register']
        OPTION_TYPE_MAP = {"group": "group", "ui_row": "tr", "ui_table": "table"}
        OPTION_TABLE = OPTION_TYPE_MAP['ui_table']
        OPTION_TR = OPTION_TYPE_MAP['ui_row']
        OPTION_TH = 'th'
        PARAMS = 'params'
        DECOMPOSITION_HINTS = 'decomposition'
        GROUP = 'group'
        CONTAINER = 'container'
        XML_SAVE = 'xml_save'
        REMOVABLE = 'removable'
        FILE_KIND = "file_kind"
        CLI_EDITABLE = "cli_editable"
        NOTE = "note"

    littleOrder = "little"
    bigOrder = "big"
    byte_order = bigOrder
    MAX_USER_NOTE_LENGTH = 500

    name: str = None
    parent: 'IComponent' = None
    offset = None
    requested_offset = None
    """
    size is the space that the data will eventually take in the binary, after encryption (and possibly others)
    """
    _size = None
    _note = None
    value = None
    previous_value = None
    value_formula = None
    decomposition_formula = None
    default_value = None
    size_formula = None
    align_formula = None
    align = None
    align_with_end = None
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
    validate_formula_json = None
    decomp_dependency = None
    map_name = None
    legacy_map_name = None
    is_legacy = None
    cli_editable = None
    enabled = None

    """
    The 'exist_formula' field controls if a component is enabled and if it can be enabled.
    It's independent from the 'enabled' field and it cannot be controlled directly by the user,
    rather it's controlled by other fields
    """
    _exists = True
    _non_exist_help_text = ""
    is_built = False
    error_message = None
    _src_exists_setting = None
    _xml_save = None
    buffer = None

    index = None


    """
    GUI section
    """
    ui_params = None
    params = None
    columns = None
    component_type = None
    decomposition_hints_formula: Optional[str] = None
    decomposition: DecompositionAttributes = None
    visible: Optional[bool] = None
    node_tag = None
    xml_save_formula = None
    iterable_descendant = False
    iterable_root = None
    iterable_index = None
    original_name = None
    removable: bool = None
    MAX_GUI_TAB_LENGTH = 64
    is_overwritten = False
    file_kind = None
    user_set_value = None
    custom_actions: List[CustomActionDefinition] = None

    ui_params_class = UiParams
    params_class = ComponentParams

    def __init__(self, xml_node, **kwargs):
        self._init_properties(xml_node, kwargs)
        self.append_to_parent()
        if self._should_omit_parsing(xml_node):
            return
        self._parse_basic_attributes(xml_node)
        self._parse_additional_attributes(xml_node)
        self._parse_gui_attributes(xml_node)
        if self._skip_calculates:
            self.decomposition = DecompositionAttributes(self.decomposition_hints_formula)
        if self.value is not None and self.buffer is None:
            self.parse_string_value(self.value)
        self._parse_children(xml_node, **kwargs)
        is_decomposition_child = self.buffer is not None
        if is_decomposition_child and self.size is None and self.value is None:
            self.size = self.buffer.tell() - self.offset
            self.buffer.seek(-self.size, os.SEEK_CUR)
            self.value = self.buffer.read(self.size)
        self._parse_custom_actions(xml_node)

        self.validate()
        self.validate_ui_params()
        self._data_used_for_building = False
        self.id_setting_name = ''
        self.id_setting_value = ''
        self.custom_error = None
        if is_decomposition_child:
            self.is_built = True

    @property
    def display_name(self) -> str:
        """Returns name in CLI and label for GUI."""
        return self.ui_params.label if LibConfig.isGui else self.name

    def update_from_buffer(self, buffer, current_offset=0):
        if self.offset is None:
            self.offset = current_offset
        elif self.offset < current_offset:
            raise ComponentException(f'Cannot update component from buffer - requested offset is smaller then '  # nosec
                                     f'current buffer offset: 0x{self.offset:X} < 0x{current_offset:X}', self.name)
        else:
            current_offset = self.offset

        self.buffer = buffer

        for child in self.children:
            current_offset = child.update_from_buffer(buffer, current_offset)
        children_size = current_offset - self.offset

        # We have to reset size of the field - it should be either calculated from size_formula or taken from children
        # because field 'size' will be either None or will store value from previous decomposition (which we don't want)
        self.size = None
        if self.size_formula is not None:
            self.size = self.calculate_value(self.size_formula)
        elif self.size is None and self.children:
            self.size = children_size
        if self.size is None:
            raise ComponentException("Cannot update component from buffer - size is not specified and component "
                                     "doesn't have any children", self.name)
        if self.size < children_size:
            raise ComponentException(f'Cannot update component from buffer - requested size is smaller then '
                                     f'size of all children: 0x{self.size:X} < 0x{children_size:X}', self.name)
        current_offset = self.offset + self.size

        self.set_value(buffer[self.offset:self.offset + self.size])

        return current_offset

    def _parse_gui_attributes(self, xml_node):
        gui_params = self._parse_attribute(xml_node, UiParams.xml_tag, False)
        self.ui_params: UiParams = self.ui_params_class(gui_params, component=self)

    def _parse_basic_attributes(self, xml_node):
        """Creates all basic formulas, without calculating them"""
        self._parse_size(xml_node)
        self._parse_align_tag(xml_node)
        self.requested_offset = self._parse_attribute(xml_node, self.Tags.OFFSET, False, None)
        self._parse_value_tag(xml_node)
        self.byte_order = self._parse_attribute(xml_node, self.Tags.ORDER, False, self.bigOrder)
        self.value_formula = self._parse_attribute(xml_node, self.Tags.CALCULATE, False, None)
        self.decomposition_formula = self._parse_attribute(xml_node, self.Tags.DECOMPOSITION_CALCULATE, False, None)
        self.padding_formula = self._parse_attribute(xml_node, self.Tags.PADDING, False, None)
        self.align_with_end = self._parse_attribute(xml_node, self.Tags.ALIGN_WITH_END, required=False, default=None)
        self.align_with_end = Converter.string_to_bool(self.align_with_end) if self.align_with_end is not None else None
        self.encryption_formula = self._parse_attribute(xml_node, self.Tags.ENCRYPT, False, None)
        self.offline_encryption_settings_path = self._parse_attribute(xml_node, self.Tags.OFFLINE_ENCRYPTION_SETTINGS,
                                                                      False, None)
        self.iv_source = self._parse_attribute(xml_node, self.Tags.IV, False, None)
        self.save_file_path = self._parse_attribute(xml_node, self.Tags.SAVE_FILE_PATH, False, None)
        self.dependency_formula = self._parse_attribute(xml_node, self.Tags.DEPENDENCY, False, None)
        self.duplicates_formula = self._parse_attribute(xml_node, self.Tags.DUPLICATES, False, None)
        self.validate_formula = self._parse_attribute(xml_node, self.Tags.VALIDATE_FORMULA, False, None)
        self.xml_save_formula = self._parse_attribute(xml_node, self.Tags.XML_SAVE, False, None)
        self.fill = self._parse_attribute(xml_node, self.Tags.FILL, False, None)
        self.removable = Converter.string_to_bool(self._parse_attribute(xml_node, self.Tags.REMOVABLE, False, "true"))
        self._parse_encryption_tag(xml_node)
        self.map_name = self._parse_attribute(xml_node, self.Tags.MAP_NAME, False, None)
        self.legacy_map_name = self._parse_attribute(xml_node, self.Tags.LEGACY_MAP_NAME, False, None)
        self.decomposition_hints_formula = self._parse_attribute(xml_node, self.Tags.DECOMPOSITION_HINTS, False, None)
        self.file_kind = self._parse_attribute(xml_node, self.Tags.FILE_KIND, False, None)
        self.cli_editable = self._parse_attribute(xml_node, self.Tags.CLI_EDITABLE, required=False, default=None)
        self.cli_editable = Converter.string_to_bool(self.cli_editable) if self.cli_editable is not None else None
        self.params = self.params_class(self._parse_attribute(xml_node, self.Tags.PARAMS, False), self.size,
                                        self.string_value_converter, component=self)

    def _parse_validate_attribute(self):
        if not self.validate_formula:
            return None

        validate_formula_json = None
        try:
            validate_formula_json = parse_json_str(self.validate_formula)
        except JSONException:
            # just continue when validate formula is not in JSON format
            pass

        return validate_formula_json

    def _parse_legacy_attribute(self, xml_node):
        is_legacy_str = self._parse_attribute(xml_node, self.Tags.LEGACY, False, None)
        self.is_legacy = Converter.string_to_bool(is_legacy_str) if is_legacy_str else is_legacy_str

    def _init_properties(self, xml_node, kwargs):
        self.name = self._get_name(xml_node)
        self.node_tag = xml_node.tag
        self._parse_kwargs(kwargs)
        self._init_iterable_desc_properties(kwargs, self)
        self.children: [IComponent] = []
        self.children_by_name = {}
        self._parse_align_byte_tag(xml_node)
        self.expr_engine = ExpressionEngine(self)
        self.component_type = type(self).__name__
        if self.index is not None and not self.iterable_descendant:
            self.name += str(self.index)
        self.previous_value = None

    def _init_iterable_desc_properties(self, kwargs, component):
        if self.parent and self.parent.iterable_descendant:
            self.parent._init_iterable_desc_properties(kwargs, component)  # pylint: disable=protected-access

    def _parse_align_tag(self, xml_node):
        self.align_formula = self._parse_attribute(xml_node, self.Tags.ALIGN, False, None)
        if self.buffer is not None and self.align_formula is not None:
            self.align = self.calculate_value(self.align_formula)
            if self.align > self.buffer.max_size:
                raise ComponentException("Alignment of component exceeds buffer size.", self.name)

            if self.align != 0 and (self.buffer.tell() % self.align) != 0:
                difference = self.align - (self.buffer.tell() % self.align)
                self.offset = self.buffer.tell() + difference
                self.buffer.seek(self.offset)

    def _parse_align_byte_tag(self, xml_node):
        xml_align_byte = self._parse_attribute(xml_node, self.Tags.ALIGN_BYTE, False, None)
        if xml_align_byte is not None:
            self.align_byte = Converter.string_to_bytes(xml_align_byte)
            return
        if self.align_byte is not None:
            return
        if self.align_byte is None and self.parent is not None and self.parent.align_byte is not None:
            if self.parent.align_byte != LibConfig.defaultPaddingValue:
                self.align_byte = self.parent.align_byte
                return
        if self.align_byte is None:
            self.align_byte = LibConfig.defaultPaddingValue

    def _parse_size(self, xml_node):
        if self.Tags.SIZE in xml_node.attrib:
            self.size_formula = xml_node.attrib[self.Tags.SIZE]
            try:
                # parse size if possible
                self.size = self.calculate_value(formula=self.size_formula, allow_calculate=True)
            except LibException:
                # If it's not possible then it will be resolved during build
                pass

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    def _parse_value_tag(self, xml_node):
        if self.Tags.VALUE in xml_node.attrib:
            self.value = xml_node.attrib[self.Tags.VALUE]
        elif self.buffer is not None:
            if not self.requested_offset:
                self.offset = self.buffer.tell()
            else:
                self.offset = self.calculate_value(self.requested_offset)
            if self.offset < self.buffer.tell() and not self.random_access:
                raise ComponentException(
                    f"Requested offset {self.requested_offset} is smaller than current offset {self.buffer.tell()}")
            self.buffer.seek(self.offset)
            if self.Tags.SIZE in xml_node.attrib:
                if self.buffer.max_size < self.offset + self.size:
                    raise ComponentException(f"Buffer size too small, failed to read at offset {self.offset}")
                self.value = self.buffer.read(self.size)

    def _parse_encryption_tag(self, xml_node):
        if self.Tags.ENCRYPTION_MODE in xml_node.attrib:
            try:
                self.encryption_mode = AesEncryption.parse_mode(xml_node.attrib[self.Tags.ENCRYPTION_MODE])
            except LibException as e:
                raise ComponentException(str(e), self.name) from e

    def append_to_parent(self):
        """Append component to its parent if the parent is defined."""
        if self.parent is not None:
            self.parent.children.append(self)
            if self.name not in self.parent.children_by_name:
                self.parent.children_by_name[self.name] = self

    def _parse_kwargs(self, kwargs):
        self.buffer = kwargs.get('buffer')
        self.random_access = kwargs.get('random_access')
        self.index = kwargs.get('index')
        if self.index is not None:
            del kwargs['index']
        self.parent = kwargs.get('parent')
        self.is_decomposition_node = kwargs.get('is_decomposition_node', False)
        self._skip_calculates: bool = kwargs.get('skip_calculates', False)
        if self.componentFactory:
            is_root = kwargs.get("is_root", False)
            if is_root:
                self.componentFactory.root = self
                del kwargs["is_root"]
            self.root_component = self.componentFactory.root

    def _should_omit_parsing(self, xml_node):
        self.calc_only = self._parse_attribute(xml_node, self.Tags.CALC_ONLY, False, None)
        self.calc_only = Converter.string_to_bool(self.calc_only) if self.calc_only is not None else None
        self.enabled_formula = self._parse_attribute(xml_node, self.Tags.ENABLED, False, None)
        try:
            if not self.is_enabled():
                return True
        except (ValueError, ComponentException, LibException):
            # this error may occur because of non-initialized fields that enabled formula may refer to,
            # so it should not be thrown. If we cannot determine if component is disabled, we cannot resign parsing it
            self.enabled = None
        return False

    def _parse_custom_actions(self, xml_node):
        self.custom_actions = []
        custom_actions = self._parse_attribute(xml_node, self.Tags.CUSTOM_ACTIONS, False, "")

        if custom_actions == "":
            return

        try:
            actions_list = parse_json_str(custom_actions)
        except JSONException as e:
            raise ComponentException(f"Cannot parse custom actions for {self.display_name}") from e

        for action in actions_list:
            custom_action = self.CustomActionDefinition.from_action_dict(action)
            self.custom_actions.append(custom_action)

    def is_setting(self):
        if self.parent and self.parent.node_tag == LibConfig.settingsTag:
            return True
        if self.parent:
            return self.parent.is_setting()
        return False

    @classmethod
    def get_name(cls, xml_node):
        if cls.Tags.NAME in xml_node.attrib:
            return xml_node.attrib[cls.Tags.NAME]
        return xml_node.tag

    def _get_name(self, xml_node):
        return self.get_name(xml_node)

    def validate(self):
        if self.encryption_formula and not self.encryption_mode:
            raise ComponentException(f"'{self.Tags.ENCRYPTION_MODE}' is required when '{self.Tags.ENCRYPT}' "
                                     f"attribute was specified", self.name)

        if self.align_formula and self.requested_offset:
            raise ComponentException(f"You can use only one at a time: {self.Tags.OFFSET} or {self.Tags.ALIGN}",
                                     self.name)

    def validate_ui_params(self):
        self.ui_params.validate()

    def validate_during_overriding(self):
        pass

    @property
    def xml_save(self):
        if self.xml_save_formula:
            self._xml_save = self.calculate_value(self.xml_save_formula)
        return self._xml_save

    @property
    def max_str_input_length(self):
        return None

    @xml_save.setter
    def xml_save(self, value):
        self._xml_save = value

    def _parse_additional_attributes(self, xml_node):  # pylint: disable=unused-argument
        self.validate_formula_json = self._parse_validate_attribute()

    def get_parsed_string_value(self, value):
        if not value:
            raise ComponentException("Value cannot be empty", self.name)
        return self.string_value_converter(value)

    @staticmethod
    def string_value_converter(val: str):
        try:
            return Converter.string_to_int(val)
        except LibException:
            pass
        try:
            return Converter.string_to_bool(val)
        except ValueError as e:
            raise ValueException("Couldn't parse into component's value.", val) from e

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        """
        Parse requested string value and apply required changes to component.
        :param value: New value as a string.
        :return: List of tuples of modified components instances and sets of pre-change PropertyState instances.
        """
        change_state_list = []
        old_val = self.value
        self.set_value(self.get_parsed_string_value(value))
        previous_user_set_value = self.user_set_value
        self.user_set_value = value
        if old_val != self.value:
            change_state_list.append((self, {PropertyState(PropertyState.SupportedProperties.VALUE, old_val)}))
        if previous_user_set_value != self.user_set_value:
            change_state_list.append((self, {PropertyState(PropertyState.SupportedProperties.USER_SET_VALUE,
                                                           previous_user_set_value)}))

        return change_state_list

    def _parse_children(self, xml_node, **kwargs):
        if xml_node is None or not len(xml_node):  # pylint: disable=use-implicit-booleaness-not-len
            return
        try:
            kwargs['parent'] = self
            for child_node in xml_node:
                if child_node.tag != 'aliases':
                    self.componentFactory.create_component(child_node, **kwargs)
        except ComponentException as ex:
            self.trace_exception(ex)

    def set_value(self, value):
        """
        Set component value.
        :param value: New value.
        """
        self._validate_iterable(value)
        self._validate_value_list(value)
        self.previous_value = self.value
        self.value = value

    def restore_previous_value(self):
        if self.previous_value is not None:
            self.value = self.previous_value

    def _validate_iterable(self, value):
        if getattr(self, "iterable_root") and value is not None and value != '':
            self.iterable_root.validate_child_value(self, value)

    def _validate_value_list(self, value):
        if self.params and self.params.is_value_list() and not self.params.is_in_value_list(value):
            error_msg = "Value does not match any of the values in list."
            if LibConfig.isGui:
                values_list = [f"'{k}' : '{self.display_func(v)}'" for k, v in self.params.get_all_from_value_list()]
            else:
                values_list = [str(self.display_func(v)) for v in self.params.get_all_values_from_value_list()]
            raise ValidateException(error_msg, self.display_func(value),
                                    value_list=', '.join(values_list),
                                    component_name=self.name)

    def get_value_label_from_value_list(self):
        self._validate_value_list(self.value)
        if not self.params.is_value_list():
            raise ComponentException("Cannot get value label - there is no value list.", self.name)
        return self.params.get_key_from_value_list(self.value)

    def trace_exception(self, exception):
        if isinstance(exception, ComponentException):
            exception.trace.append(self.name)
        raise exception

    def __str__(self):
        return self.name

    def len(self):
        if self.size is not None:
            return self.size

        raise ComponentException("Size is unknown - object's layout hasn't been built yet", self.name)

    def get_property(self, property_name: object, allow_calculate: object = False, build_process=False) -> object:
        self._check_error()
        property_name, index_from, index_to = self.parse_property_indexing(property_name)
        component_property = self.parse_property_name(property_name)
        value = self._get_property(component_property, allow_calculate, build_process)

        if value is None:
            raise ComponentException(f"Missing handler for property: '{property_name}'", self.name)

        if index_from is None and index_to is None:
            return value

        if not isinstance(value, Iterable):
            raise ComponentException(f"'{property_name}' cannot be accessed by index", self.name)

        return self.get_value_from_index(value, index_from, index_to)

    # pylint: disable-next=unused-argument
    def _get_property(self, component_property, allow_calculate=False, report_usage=False):
        if component_property == self.ComponentProperty.VALUE:
            if self.value is not None:
                return self.value
            if self.has_dependencies() or self.has_duplicates():
                return None  # value is none, so it means that dependency hasn't been resolved yet
            if self.value_formula and allow_calculate:
                return self.calculate_value(formula=self.value_formula, allow_calculate=allow_calculate)
            return self.get_default_value()
        if component_property == self.ComponentProperty.DEFAULT_VALUE:
            return self.get_default_value()
        if component_property == self.ComponentProperty.IS_DEFAULT:
            return self.is_default()
        if component_property == self.ComponentProperty.SIZE:
            return self.size
        if component_property == self.ComponentProperty.OFFSET:
            return self.offset
        if component_property == self.ComponentProperty.ENABLED:
            return self.is_enabled()
        if component_property == self.ComponentProperty.INDEX:
            return self.get_table_index()
        if component_property == self.ComponentProperty.MAP_NAME:
            if LibConfig.pathSeparator in self.map_name:
                try:
                    calculated_val = self.calculate_value(formula=self.map_name, allow_calculate=allow_calculate)
                    return calculated_val
                except ComponentException:
                    return self.map_name
            return self.map_name
        if component_property == self.ComponentProperty.LEGACY_MAP_NAME:
            if LibConfig.pathSeparator in self.legacy_map_name:
                try:
                    calculated_val = self.calculate_value(formula=self.legacy_map_name, allow_calculate=allow_calculate)
                    return calculated_val
                except ComponentException:
                    return self.legacy_map_name
            return self.legacy_map_name

        if component_property == self.ComponentProperty.ENCRYPTION_MODE:
            return AesEncryption.modeTypes[self.encryption_mode]
        if component_property == self.ComponentProperty.BUFFER_SIZE:
            if self.buffer is None:
                raise ComponentException("Decomposition buffer not set properly.")
            return self.buffer.max_size
        if component_property == self.ComponentProperty.INITIAL_VECTOR:
            if not self.initial_vector:
                raise ComponentException("This component doesn't have initialisation vector for AES encryption",
                                         self.name)
            return self.initial_vector
        if component_property == self.ComponentProperty.INITIAL_VECTOR_SIZE:
            if not self.initial_vector:
                raise ComponentException("This component doesn't have initialisation vector for AES encryption",
                                         self.name)
            return len(self.initial_vector)
        if component_property == self.ComponentProperty.CHILD_COUNT:
            return len(self.children)
        if component_property == self.ComponentProperty.CHILD_COUNT_ENABLED:
            enabled_children = [child for child in self.children if child.is_enabled()]
            return len(enabled_children)
        if component_property == self.ComponentProperty.EMPTY:
            return self._is_empty()
        if component_property == self.ComponentProperty.READ_ONLY:
            return self.ui_params.read_only
        if component_property == self.ComponentProperty.VISIBLE:
            return self.ui_params.visible
        if component_property == self.ComponentProperty.VALUE_LIST:
            if self.params.is_value_list():
                return self.params.dict[ComponentParams.ParamsAttr.VALUE_LIST.value]
        return None

    def parse_property_name(self, property_name):
        try:
            return self._get_component_property(property_name)
        except Exception as e:
            values = [item.value for item in self.ComponentProperty]
            raise ComponentException(f"No such property: '{property_name}', use one of:\n   {', '.join(values)}",
                                     self.name) from e

            # Overridden, if dynamic enum is needed

    def _get_component_property(self, property_name):
        return self.ComponentProperty(property_name)

    @staticmethod
    def parse_property_indexing(property_name):
        # Examples of expected strings: data[20:128], data[512:], data[0xE:0x1A], value[0xBB:]
        match = re.match("(.+)\\[((?:0x)?.+):((?:0x)?.*)\\]", property_name)
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
        index_to = Converter.string_to_int(index_to) if index_to != '' else len(value)

        if index_from > index_to:
            value = bytes(reversed(value))
            index_from = len(value) - index_from
            index_to = len(value) - index_to

        return value[index_from:index_to]

    def get_bytes(self):
        self._check_error()
        if self.value is None:
            raise ComponentException("You can only get bytes from objects with defined value", self.name)
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
            raise ComponentException(f"Failed to get bytes from value of type '{type(self.value).__name__}', "
                                     f"error: {str(ex)}", self.name) from None

    def _get_bytes(self):
        raise ComponentException(f"Cannot get bytes from object of type '{self.component_type}'", self.name)

    def _align_bytes_to_size(self, value):
        value = bytearray(value)
        delta_length = self.size - len(value)
        if delta_length > 0:
            if self.align_with_end:
                temp_value = bytearray(self.align_byte * delta_length)
                temp_value.extend(value)
                value = temp_value
            else:
                value.extend(self.align_byte * delta_length)
        elif delta_length < 0:
            raise ComponentException(f"Provided value is too big ({len(value)} bytes), maximum size is {self.size} "
                                     f"bytes", self.name)
        return value

    @property
    def exists(self):
        if self.parent and not self.parent.exists:
            return False
        return self._exists

    def parse_non_exist_reason(self, source_setting):
        # If source setting has value_list, reason for disabling dependant setting should contain value_list key
        # instead of value
        value_to_display = str(source_setting.value)
        if source_setting.value is not None and \
                source_setting.params.is_value_list() and \
                source_setting.params.is_in_value_list(self.src_exists_setting.value):
            value_to_display = source_setting.params.get_key_from_value_list(self.src_exists_setting.value)

        reason = f"cannot be enabled with {source_setting.display_name} set to {value_to_display}"
        return reason

    def set_exists(self, exists_value: bool, src_setting_ref) -> List[ComponentPreChangeState]:
        self._exists = exists_value
        self.src_exists_setting = src_setting_ref
        self.non_exist_help_text = self.parse_non_exist_reason(src_setting_ref)

        states = set()
        states.add(PropertyState(PropertyState.SupportedProperties.EXISTS, self.exists))
        states.add(PropertyState(PropertyState.SupportedProperties.NON_EXIST_HELP_TEXT,
                                 self.non_exist_help_text))
        states.add(PropertyState(PropertyState.SupportedProperties.SRC_EXISTS_SETTING,
                                 src_setting_ref))
        modified_settings = []
        modified_settings.append((self, states))

        # Collecting all group-type children of setting affected by exists change
        # to pass them along with dependencies to GUI, to perform update of these
        # children as well
        for component in self.gather_all_group_type_children():
            comp_state = set()
            comp_state.add(PropertyState(PropertyState.SupportedProperties.EXISTS, component.exists))
            comp_state.add(PropertyState(PropertyState.SupportedProperties.NON_EXIST_HELP_TEXT,
                                         component.non_exist_help_text))
            comp_state.add(PropertyState(PropertyState.SupportedProperties.SRC_EXISTS_SETTING,
                                         component.src_exists_setting))
            modified_settings.append((component, comp_state))

        return modified_settings

    def gather_all_group_type_children(self):
        all_level_children = []
        for child in self.children:
            if child.node_tag == IComponent.Tags.GROUP:
                all_level_children.append(child)
                if child.children:
                    all_level_children.extend(child.gather_all_group_type_children())
        return all_level_children

    @property
    def src_exists_setting(self):
        """
        Returns source setting of exists dependency
        :return: source setting of exists dependency
        """
        if not self._src_exists_setting and self._exists and self.parent is not None and not self.parent.exists:
            return self.parent.src_exists_setting
        return self._src_exists_setting

    @src_exists_setting.setter
    def src_exists_setting(self, value):
        """
        Sets source setting of exists dependency
        :param value: source setting of exists dependency
        """
        self._src_exists_setting = value

    @property
    def non_exist_help_text(self):
        if not self._non_exist_help_text and self._exists and self.parent is not None and not self.parent.exists:
            return self.parent.non_exist_help_text
        return self._non_exist_help_text

    @non_exist_help_text.setter
    def non_exist_help_text(self, value):
        self._non_exist_help_text = value

    def is_enabled(self):
        if self.enabled_formula and not self._skip_calculates:
            try:
                self.enabled = self._parse_enabled()
            except(ValueError, ComponentException, LibException) as e:
                self.enabled = None
                self.trace_exception(e)
        elif self.enabled is None:
            self.enabled = True
        return self.exists and self.enabled

    def _parse_enabled(self):
        enabled = self.calculate_value(formula=self.enabled_formula, allow_calculate=True)
        if not isinstance(enabled, bool):
            raise ComponentException(f"Invalid formula for '{self.Tags.ENABLED}' - result is not bool: "
                                     f"{self.enabled_formula}", self.name)
        return enabled

    def _is_empty(self):
        raise ComponentException(f"Cannot check if object of type '{self.component_type}' is empty", self.name)

    def load_offline_encryption_settings(self):
        if self.offline_encryption_settings_path is None:
            return
        settings_node = self.calculate_value(formula=self.offline_encryption_settings_path)
        try:
            self.offline_encryption_settings = OfflineEncryptionSettings(settings_node)
        except LibException as e:
            raise ComponentException(f"Failed to load offline encryption settings, "
                                     f"reason: {str(e)}", self.name) from None

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
            raise ComponentException(f'{OfflineEncryptionSettings.Tags.STORE_DIR} must not be empty')
        file_names = self.offline_encryption_settings.get_files_names(self.name)
        # Load encrypted data
        encrypted_path = os.path.join(store_dir, file_names.encrypted)  # pylint: disable=no-member
        if not os.path.isfile(encrypted_path):
            raise ComponentException(f"{encrypted_path} is missing - it should contain encrypted data", self.name)
        with open_file(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        # Load unencrypted data - just to verify that it differs from those encrypted
        unencrypted_path = os.path.join(store_dir, file_names.unencrypted)  # pylint: disable=no-member
        if not os.path.isfile(unencrypted_path):
            raise ComponentException(f"{unencrypted_path} is missing - it's used to check if data is encrypted "
                                     f"(it must differ from encrypted data)", self.name)
        with open_file(unencrypted_path, 'rb') as f:
            unencrypted_data = f.read()
        # Compare data
        if unencrypted_data == encrypted_data:
            raise ComponentException(f"It seems that data were not encrypted:\n{unencrypted_path}\nis the same as:\n"
                                     f"{encrypted_path}", self.name)
        self.loaded_encrypted_data = encrypted_data
        self.size = len(self.loaded_encrypted_data)
        # Load initialisation vector
        iv_path = os.path.join(store_dir, file_names.iv)  # pylint: disable=no-member
        if not os.path.isfile(iv_path):
            raise ComponentException(f"{iv_path} is missing - it should contain initialisation vector (can be filled "
                                     f"with 0xFF if used encryption mode doesn't use initialisation vector)", self.name)
        with open_file(iv_path, 'rb') as f:
            self.initial_vector = f.read()
        if len(self.initial_vector) != AesEncryption.aesBlockSizeBytes:
            raise ComponentException(f"Length of initialisation vector is {len(self.initial_vector)} but should be "
                                     f"{AesEncryption.aesBlockSizeBytes}", self.name)

    def handle_offline_encryption_save(self):
        store_dir = self.offline_encryption_settings.store_dir
        if not store_dir:
            raise ComponentException(f'{OfflineEncryptionSettings.Tags.STORE_DIR} must not be empty')
        if os.path.isfile(store_dir):
            raise ComponentException(f"Cannot store data to encrypt in: {store_dir}, it's a file.", self.name)
        file_names = self.offline_encryption_settings.get_files_names(self.name)
        unencrypted_path = os.path.join(store_dir, file_names.unencrypted)  # pylint: disable=no-member
        FileManager.save_binary_file(unencrypted_path, self.get_bytes())
        if self.initial_vector is not None:
            iv_path = os.path.join(store_dir, file_names.iv)  # pylint: disable=no-member
            FileManager.save_binary_file(iv_path, self.initial_vector)

    def build_layout(self, buffer, clear_build_settings=False):
        if clear_build_settings:
            self.is_built = False

        self.offset = buffer.tell()

        if not self.is_enabled():
            self.size = 0
            if self.value is None:
                self.set_value(self.get_default_value())
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
                raise ComponentException(f"Cannot set requested offset: {hex(self.offset)}, current offset is already: "
                                         f"{hex(buffer.tell())}", self.name)
            buffer.seek(self.offset)

        if self.size is None and self.size_formula is not None:
            self.size = self.calculate_value(formula=self.size_formula, allow_calculate=True)

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
                self.initial_vector = AesEncryption.create_initialisation_vector()
            elif self.is_offline_encryption_load():
                self.handle_offline_encryption_load()
        elif self.encryption_formula is not None:
            # encryption might influence the size
            try:
                self.encryption_key_component = self.calculate_value_from_path(self.encryption_formula)
                if self.encryption_key_component.is_enabled():
                    initial_vector = None
                    if self.iv_source is not None:
                        initial_vector = self.calculate_value(self.iv_source)
                    if not initial_vector:
                        self.initial_vector = AesEncryption.create_initialisation_vector()
                    else:
                        self.initial_vector = initial_vector
                    # encryption might increase the size of the component
                    self.size = self.encryption_key_component.get_encrypted_data_size(self.size,
                                                                                      self.encryption_mode)
                else:
                    self.initial_vector = AesEncryption.get_empty_initialisation_vector()
                    self.encryption_key_component = None
            except LibException as e:
                raise ComponentException(f"Encryption failed: {str(e)}", self.name) from None

        buffer.seek(self.offset + self.size)

    def _build_layout(self):
        if self.value_formula and not self.size:
            try:
                value = self.calculate_value(formula=self.value_formula, build_process=True)
                self.size = len(value)
                self.set_value(value)
            except (TypeError, AttributeError) as ex:
                raise ComponentException(f"Cannot get size from the result of the formula '{self.value_formula}' "
                                         f"because: {ex}", self.name) from None

        if self.value_formula and self.value is None:
            try:
                value = self.calculate_value(formula=self.value_formula, allow_calculate=True, build_process=True)
                self.set_value(value)
            except (ComponentException, AttributeError):
                # Use default value as a temporary value
                # - proper value will be calculated at a later stage
                self.set_value(self.get_default_value())

    def check_validate_formula(self):
        if self.validate_formula:
            validate_string = self.validate_formula
            error_message = ''
            severity = ''
            if self.validate_formula_json:
                validate_string = self.validate_formula_json[self.Tags.CALCULATE]
                error_message = self.validate_formula_json[CustomError.messageTag]
                severity = self.validate_formula_json.get(CustomError.severityTag)
            if not self.calculate_value(validate_string, True):
                if severity and severity == Severity.WARNING.value:
                    print(f'Warning for {self.display_name}:\n{error_message}')
                    return
                if not error_message:
                    error_message = self.validate_formula
                raise ComponentException(f'\nValidation formula failed:\n  {error_message}', self.display_name)

    def build(self, buffer):
        if not self.is_enabled() or self.is_built:
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
                except OverflowError as e:
                    raise ComponentException(f"Fill value: {self.fill} is longer than 1 byte", self.name) from e
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
                self.set_value(buffer.read(self.size))

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
                    self.set_value(
                        self.encryption_key_component.encrypt(self.value, self.encryption_mode, self.initial_vector))
                    buffer.seek(self.offset)
                    buffer.write(self.value)
            except Exception as e:
                raise ComponentException(f"Failed to encrypt: {str(e)}", self.name) from None

        if self.offset is not None:
            # Let's also validate if we've written the proper number of bytes into the buffer
            size_in_buffer = buffer.tell() - self.offset
            if size_in_buffer != self.size:
                raise ComponentException(f"Invalid final size of the component, expected: {self.size} but is "
                                         f"{size_in_buffer}", self.name)

        self.is_built = True

        if self.save_file_path is not None:
            path = self.calculate_value(self.save_file_path)
            if path:
                FileManager.save_binary_file(path, self.get_bytes())
                print(f"Content of {self.get_string_path()} saved to {path}\n")

    def _build(self, _):
        if self.value_formula:
            self.set_value(self.calculate_value(formula=self.value_formula, build_process=True))

    def validate_file_size(self):
        pass

    def _add_padding(self, buffer):
        if self.padding_formula is not None:
            padding_value = self.calculate_value(self.padding_formula, allow_calculate=True)
            if not isinstance(padding_value, int):
                raise ComponentException(f"Padding formula must result in an integer, but is "
                                         f"{type(padding_value).__name__}", self.name)
            new_size = align_value(self.size, padding_value)
            padding_bytes = LibConfig.defaultPaddingValue if self.align_byte is None else self.align_byte
            self.padding = bytes(padding_bytes * (new_size - self.size))
            self.size = new_size
            buffer.seek(self.offset + self.size)

    def _fill_padding(self, buffer):
        if not self.padding:
            return
        if self.align_with_end:
            buffer.seek(self.offset)
            buffer.write(self.padding)
            buffer.seek(self.offset + self.size)
        else:
            buffer.seek(self.offset + self.size - len(self.padding))
            buffer.write(self.padding)

    def get_child(self, child_name):
        return self._get_child(child_name)

    def __getitem__(self, index):
        if isinstance(index, str):
            return self.get_child(index)
        if isinstance(index, int):
            if index > len(self.children):
                raise ComponentException(f"Cannot get child at index '{index}', "
                                         f"there are only {len(self.children)} children", self.name)
            return self.children[index]
        raise ComponentException(f"Cannot use '{type(index).__name__}' as component index", self.name)

    def _get_child(self, child_name):
        if self.children_by_name is None:
            raise ComponentException(f"'{self.name}' has no children", self.name)
        if child_name in self.children_by_name:
            return self.children_by_name[child_name]
        if self.iterable_descendant:
            iterable_name = f'{self.iterable_root.name}[{self.iterable_index}].{child_name}'
            if iterable_name in self.children_by_name:
                return self.children_by_name[iterable_name]
        # search among transparent gui nodes (optionTypeMap) and bit_registers (multiLevelComponentsTags)
        gui_children = filter(lambda child: child.node_tag in self.Tags.OPTION_TYPE_MAP
                              or child.node_tag in self.Tags.MULTI_LEVEL_COMPONENTS, self.children)
        for gui_node in gui_children:
            try:
                return gui_node.get_child(child_name)
            except ComponentException:
                pass
        raise ComponentException(
            f"No '{child_name}' child. Choose one of: {', '.join(self.children_by_name.keys())}", self.name)

    def remove_child(self, child_name):
        if child_name in self.children_by_name:
            child_to_remove = self.children_by_name[child_name]
            self.children.remove(child_to_remove)
            self.children_by_name.pop(child_name)

    def write_bytes_to_buffer(self, comp_bytes, buffer, offset=None):
        """
        Write bytes to the passed buffer, optionally at specified offset.
        :param comp_bytes: Bytes to write.
        :param buffer: Buffer to write to.
        :param offset: (Optional) Offset at which bytes will be written. Calculated if not passed.
        """
        if offset is not None:
            if buffer.max_size <= offset:
                raise ComponentException(
                    f"Component has offset ({offset}) higher than binary size ({buffer.max_size})!", self.name)
        else:
            offset = buffer.tell()
        if buffer.max_size < offset + len(comp_bytes):
            raise ComponentException(f"Component exceeded the binary size\n"
                                     f"Offset: {offset} Size: {len(comp_bytes)}\n"
                                     f"Maximum binary size: {buffer.max_size}", self.name)
        buffer.seek(offset)
        buffer.write(comp_bytes)

    def calculate_value(self, formula, allow_calculate=False, allow_none_return=False, build_process=False):
        return self.expr_engine.calculate_value(formula, None, allow_calculate, allow_none_return, build_process)

    def calculate_value_from_path(self, path, allow_calculate=False):
        return self.expr_engine.calculate_value_from_path(path, allow_calculate)

    def get_dependencies(self, duplicates: bool = False) -> List[Dependency]:
        if duplicates and not LibConfig.isGui:
            return []
        formula = self.duplicates_formula if duplicates else self.dependency_formula
        try:
            json_dic = parse_json_str(formula)
        except JSONException as e:
            raise ComponentException(f"Wrong json syntax: {formula}", self.name) from e

        try:
            return [DependencyFactory.create_dependency(dependency_type, properties, self, duplicates)
                    for el in json_dic for dependency_type, properties in el.items()]
        except DependencyException as e:
            raise ComponentException(str(e), self.name) from None

    def has_dependencies(self):
        return bool(self.dependency_formula)

    def has_map_name_descendant(self):
        """This method returns true if any descendant of this component has map_name attribute"""
        if not self.children:
            return False
        return any(child.map_name or child.has_map_name_descendant() for child in self.children)

    def has_value_dependency(self):
        """This method returns if this component's value comes from dependency on other setting"""
        if self.dependency_formula:
            json_dep_list = self._parse_dependency_formula()
            for dep in json_dep_list:
                if Dependency.Tags.SWITCH in dep:
                    return True
                if Dependency.Tags.GET in dep:
                    if Dependency.Tags.TARGET_PROPERTY not in dep[Dependency.Tags.GET]:
                        return True
                    if dep[Dependency.Tags.GET][Dependency.Tags.TARGET_PROPERTY] == Dependency.Targets.VALUE.value:
                        return True
        return False

    def _has_set_value_dependency(self):
        """This method returns true if setting has set dependency on value"""
        if self.dependency_formula:
            json_dep_list = self._parse_dependency_formula()
            for dep in json_dep_list:
                if Dependency.Tags.SET in dep:
                    if Dependency.Tags.TARGET_PROPERTY not in dep[Dependency.Tags.SET]:
                        return True
                    if dep[Dependency.Tags.SET][Dependency.Tags.TARGET_PROPERTY] == Dependency.Targets.VALUE.value:
                        return True
        return False

    def _parse_dependency_formula(self):
        try:
            return parse_json_str(self.dependency_formula)
        except JSONException as e:
            raise ComponentException(f"Wrong json syntax: {self.dependency_formula}", self.name) from e

    def has_duplicates(self):
        return bool(self.duplicates_formula) if LibConfig.isGui else False

    def to_xml_node(self, parent, simple_xml: bool, save_user_notes=True):
        if not self.is_setting_saveable and (not self.note or not save_user_notes):
            return
        is_gui_node = self.node_tag in self.Tags.OPTION_TYPE_MAP
        is_enablable_gui_node = is_gui_node and self.enabled_formula
        node_name = 'setting'

        if not is_gui_node or is_enablable_gui_node:
            # node that represents this component in user xml
            node = SubElement(parent, node_name, {self.Tags.NAME: self.name})
            if is_enablable_gui_node:
                node.set(self.Tags.VALUE, '0x1' if self.is_enabled() else '0x0')
            elif not is_gui_node:
                node.set(self.Tags.VALUE, self._user_xml_value())
                if self.has_annotations:
                    node.set(self.Tags.NOTE, self.note)
        # do not save group children for simple xml
        if simple_xml and is_enablable_gui_node:
            return
        if self.children_by_name:
            node_children_parent = parent
            for child in self.children_by_name.values():
                child.to_xml_node(node_children_parent, simple_xml, save_user_notes)

    def _user_xml_value(self):
        """Returns value used in user xml"""
        return self.get_value_string()

    def _raise_missing_child(self, child_tag):
        raise ComponentException(f"Missing mandatory child tag: '{child_tag}'", self.name)

    # This is used for lazy error checking. Eg.: certain types (used in settings section) try to load files
    # but they may not be needed at all. So it's convenient to set the error message when we fail to initialise
    # but only return error to user if we try to use this node.
    def _check_error(self):
        if self.error_message is not None and not LibConfig.isGui:
            raise ComponentException(self.error_message, self.name)

    def get_value_string(self):
        return self.get_val_string(self.value)

    def get_val_string(self, val):
        return None if val is None else str(val)

    def get_string_path(self):
        return f"{self.parent.get_string_path() if self.parent else ''}/{self.name}"

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
            raise ComponentException(f"Cannot find required node {tag}", self.name)
        return node

    def _parse_all_nodes(self, xml_node, tag):
        nodes = xml_node.findall(tag)
        if not nodes:
            raise ComponentException(f"Cannot find required node {tag}", self.name)
        return nodes

    def _parse_attribute(self, xml_node, tag, required=True, default=None):
        if tag not in xml_node.attrib and required:
            raise ComponentException(f"Cannot find required attribute {tag}", self.name)
        if tag in xml_node.attrib:
            return xml_node.attrib[tag]
        return default

    def get_all_children(self, children: dict):
        for child in self.descendants:
            if child.name in children:
                raise ComponentException(f"There already exists child with the name '{child.name}':"
                                         f" {child.get_string_path()}")
            children[child.name] = child

    def get_children_with_tags(self, *argv: str) -> List["IComponent"]:
        if self.children:
            return [child for child in self.children if child.node_tag in argv]
        return []

    @property
    def descendants(self) -> Generator['IComponent', None, None]:
        for child in self.children:
            yield child
            for descendant in child.descendants:
                yield descendant

    @property
    def display_user_set_value(self):
        return False

    def copy_to(self, dst):
        if type(self) != type(dst):  # pylint: disable=unidiomatic-typecheck
            raise ComponentException(
                f"Source and destination components need to have the same type. type({self.name}) != type({dst.name})")
        self._copy_to(dst)

    def _copy_to(self, dst):
        """Copies defined attributes from self to destination object.
        Copying of component specific attributes is that component responsibility."""
        dst.value = self.value
        dst.size = self.size

    @property
    def xml_save_formula_is_static(self):
        """Returns true if xml formula does not contain any expression"""
        return self.xml_save_formula.lower().strip() in ["true", "false"]

    @property
    def is_setting_saveable(self):
        if self.xml_save_formula:
            return self.xml_save
        if self.cli_editable is not None:
            return self.cli_editable
        if self.has_value_dependency():
            return False
        if self.value_formula is not None:
            return False
        return True

    def is_node_overridable(self):
        if self.cli_editable is not None:
            return self.cli_editable
        if self.xml_save:
            return True
        # setting should be overridable if it has set dependency on value property
        if self.has_value_dependency() and not self._has_set_value_dependency():
            return False
        if self.value_formula:
            return False
        return True

    def add_decomp_dependency(self, sett):
        self.decomp_dependency.append(sett)

    def _update_decomp_dependency(self):
        with open_file(self.value, 'rb') as file:
            with Buffer(file.fileno(), 0, access=ACCESS_READ) as buffer:
                for dep in self.decomp_dependency:  # pylint: disable=not-an-iterable
                    dep.update_from_buffer(buffer)

    def initialize_defaults(self):
        if self.node_tag not in self.Tags.OPTION_TYPE_MAP:
            if self.value is not None:
                self.default_value = self.value
            elif self.value_formula and not self._skip_calculates:
                try:
                    self.default_value = self.calculate_value(self.value_formula, False)
                except Exception:
                    self.default_value = None
        for child in self.children:
            child.initialize_defaults()

    def get_default_value(self):
        if self.default_value:
            return self.default_value
        return 0

    def is_default(self):
        return bool(self.value == self.get_default_value())

    @property
    def enablable(self):
        return self.enabled_formula is not None

    @property
    def non_default_settings(self):
        return [setting for setting in self.children if setting.has_non_default_value
                or setting.name == 'default_platform']

    @property
    def settings_with_note(self):
        return [setting for setting in self.children if setting.has_annotations]

    @property
    def has_non_default_value(self):
        return self.value != self.default_value and not \
            ((self.value == '' or self.value == b'') and self.default_value is None)

    @property
    def has_annotations(self):
        return self.params.note_available and self.note

    @property
    def map_data(self) -> [MapData]:
        """Returns list of start offset, length, intent, area name"""
        data: List = []
        intent = 0
        map_name = None
        if LibConfig.legacyMap:
            map_name = self.get_property("legacy_map_name", True) if self.legacy_map_name and self.size \
                                                                     and self.offset is not None else None
        if map_name is None:
            map_name = self.get_property("map_name", True) if self.map_name and self.size and self.offset \
                                                              is not None else None
        if map_name:
            data.append(MapData(self.offset, self.size, 0, map_name))
            intent = 1

        for child in self.children:
            if child.is_enabled() and child.map_data:
                leveled = (MapData(x.offset, x.length, x.indent + intent, x.map_name) for x in child.map_data)
                data.extend(leveled)
        return data

    def clear_data(self):
        self._clear_data()
        for child in self.children:
            child.clear_data()

    def _clear_data(self):
        pass

    def semideepcopy(self):
        """Make a copy of the component similar to a deep copy."""
        # pylint: disable=attribute-defined-outside-init
        copied = copy(self)
        copied.children = []
        copied.children_by_name = {}
        copied.expr_engine = ExpressionEngine(copied)
        self._copy_params_to(copied)

        if self.children is not None:
            for child in self.children:
                child_copy = child.semideepcopy()
                child_copy.parent = copied
                child_copy.append_to_parent()
        return copied
        # pylint: enable=attribute-defined-outside-init

    def _copy_params_to(self, destination_component):
        destination_component.params = copy(self.params)
        if destination_component.params and hasattr(destination_component.params, 'dict'):
            destination_component.params.dict = copy(self.params.dict)
        destination_component.ui_params = copy(self.ui_params)
        destination_component.ui_params.property_definitions = copy(self.ui_params.property_definitions)

    @property
    def path(self):
        path = self.name
        component = self.parent if self.parent else self
        while component.parent and component.root_component is not component:
            path = f'{component.name}/{path}'
            component = component.parent
        return path

    @property
    def data_used_for_building(self):
        return self._data_used_for_building

    def set_data_used_for_building(self, val):
        self._data_used_for_building = val

    def decomposition_reference(self):
        return self.value_formula and f'/{LibConfig.decompositionTag}/' in self.value_formula

    def check_custom_error(self, build_check=False):
        """
        Check if component has specified custom error and if it occurs.
        :param build_check: Check occurred during build
        """
        if self.validate_formula_json and hasattr(self.root_component, 'children') and \
                self.root_component.children and len(self.root_component.children) != 0:

            # if root component contains any children, that means the configuration has been parsed
            # and JSON format in validate formula means that there is a Custom Error
            custom_error = CustomError(self)
            self.custom_error = custom_error if custom_error.occurs(build_check) else None

    def original_component_name(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns names of container and setting referred by get dependency of this component or (None, None) if setting
        does not have get dependency from different container.
        """
        DependencyInfo = namedtuple('DependencyInfo', 'container_name component_name')
        if not self.dependency_formula:
            return None, None
        for dependency in self._parse_dependency_formula():
            get_obj = dependency.get('get')
            if get_obj is not None:
                if isinstance(get_obj, str):
                    elements = dependency['get'].split('/')
                    if len(elements) == 2:
                        parts = elements[1].split('.')
                        if len(parts) == 1 or (len(parts) == 2 and parts[1] == self.Tags.VALUE):
                            return DependencyInfo(elements[0], parts[0])
        return DependencyInfo(None, None)

    @property
    def note(self) -> Optional[str]:
        return self._note

    @note.setter
    def note(self, value: Optional[str]):
        if value is not None:
            self._validate_note(value)
        self._note = value

    def _validate_note(self, note: str):
        if len(note) > self.MAX_USER_NOTE_LENGTH:
            raise ValidateException("User note too long", note, component_name=self.name)

    def display_func(self, val):
        return self.get_val_string(val)
