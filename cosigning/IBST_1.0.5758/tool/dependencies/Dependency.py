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

from enum import Enum
from typing import List, Optional

from ..AttributeGroup import UiParams
from ..Errors import Errors
from ..LibConfig import LibConfig
from ..LibException import DependencyException
from ..PropertyState import ComponentPreChangeState
from ..UniqueKey import UniqueKey, VersionedName


class Dependency:
    tag = None
    value_list = None
    bit_low = None
    bit_high = None
    src_setting_ref = None
    dst_setting_ref = None
    referenced_set_name = None
    setting_property = None
    referenced_key = None
    calculate = None
    new_value = None
    source_name = None
    destination_name = None

    class Tags:
        GET = "get"
        SWITCH = "switch"
        SET = "set"
        PATH = "path"
        BIT_LOW = "bit_low"
        BIT_HIGH = "bit_high"
        SOURCE = "source"
        VALUE_LIST = "value_list"
        DEFAULT = "default"
        CALCULATE = "calculate"
        TARGET_PROPERTY = "target_property"
        GUI_ONLY = "gui_only"

    class Targets(Enum):
        VALUE = "value"
        READ_ONLY = UiParams.Tags.READ_ONLY
        VISIBLE = UiParams.Tags.VISIBLE
        VALUE_LIST = "value_list"
        ENABLED = "enabled"
        EXISTS = "exists"
        XML_SAVE = "xml_save"
        PATH = "path"

    gui_only_targets = [Targets.READ_ONLY, Targets.VISIBLE]

    def __init__(self, properties, owner_setting_ref, is_duplicate=False):
        self.owner_setting_ref = owner_setting_ref
        self.is_duplicate = is_duplicate
        self.target_property = self.Targets.VALUE
        self.owner_key = None
        self.referenced_key = None
        self.dst_container_key: Optional[UniqueKey] = None
        self.src_container_key: Optional[UniqueKey] = None
        self.gui_only: bool = False

        # If 'properties' is of type str then assume that it's simply a path to some other setting
        if isinstance(properties, str):
            self._parse_referenced_setting_path(properties)
        elif isinstance(properties, dict):
            self._parse_properties_dict(properties)
        else:
            raise DependencyException(f"Unsupported type of dependency properties: {type(properties).__name__} "
                                      f"for dependency: {self.tag}", self)

    @property
    def affects_only_gui(self):
        return self.gui_only or self.target_property in Dependency.gui_only_targets

    def _parse_referenced_setting_path(self, path):
        if not path.strip():
            raise DependencyException(f"Specified dependency path cannot be empty, in dependency: {self.tag}", self)
        parts = path.split(LibConfig.pathSeparator)
        self.referenced_set_name, self.setting_property, self.referenced_key = self._parse_dependency_path(parts)

    def _parse_dependency_path(self, parts):
        plug_key = VersionedName()
        cont_key = VersionedName()

        self._raise_if_dependency_is_referencing_iterable_setting(parts)

        if len(parts) == 3:  # parse plugin_key/cont_key/setting
            plug_key = VersionedName(name_ver=parts[0])
            cont_key = VersionedName(name_ver=parts[1])
            set_subparts = parts[2].rsplit(".", maxsplit=1)
        elif len(parts) == 2:  # parse cont_key/setting
            cont_key = VersionedName(name_ver=parts[0])
            set_subparts = parts[1].rsplit(".", maxsplit=1)
        elif len(parts) == 1:  # parse this/setting
            set_subparts = parts[0].rsplit(".", maxsplit=1)
        else:
            raise DependencyException(f"Failed to parse dependency: {parts}", self)

        set_name = set_subparts[0]
        set_property = set_subparts[1] if len(set_subparts) == 2 else None
        unique_key = UniqueKey(cont_key, plug_key)
        return set_name, set_property, unique_key

    def _raise_if_dependency_is_referencing_iterable_setting(self, parts):
        for part in parts:
            if "[" in part and "]" in part:
                raise DependencyException("Dependencies to iterable settings are not permitted.", dependency=self,
                                          owner_component=self.owner_setting_ref)

    def _parse_properties_dict(self, properties):
        if self.Tags.PATH not in properties:
            raise DependencyException(f"{self.Tags.PATH} is missing from dependency: {self.tag}", self)
        self._parse_referenced_setting_path(properties[self.Tags.PATH])
        if self.Tags.BIT_LOW in properties or self.Tags.BIT_HIGH in properties:
            if self.Tags.BIT_LOW not in properties or self.Tags.BIT_HIGH not in properties:
                raise DependencyException(f"Both {self.Tags.BIT_LOW} and {self.Tags.BIT_HIGH} must be specified if "
                                          f"at least one of them is given", self)
            self.bit_low = properties[self.Tags.BIT_LOW]
            self.bit_high = properties[self.Tags.BIT_HIGH]

            if self.bit_low > self.bit_high:
                raise DependencyException(f"{self.Tags.BIT_LOW} cannot be greater then {self.Tags.BIT_HIGH}", self)
        if self.Tags.TARGET_PROPERTY in properties:
            tag_content = properties[self.Tags.TARGET_PROPERTY]
            try:
                self.target_property = self.Targets(tag_content)
            except ValueError as e:
                raise DependencyException(f"{tag_content} target property is not supported", self) from e
        if self.Tags.CALCULATE in properties:
            self.calculate = properties[self.Tags.CALCULATE]
        if self.Tags.GUI_ONLY in properties and properties[self.Tags.GUI_ONLY] == 'true':
            self.gui_only = True

    def set_referenced_setting(self, referenced_setting_ref):
        if self.get_bit_count() and (not isinstance(referenced_setting_ref.get_default_value(), int) or
                                     not isinstance(self.owner_setting_ref.get_default_value(), int)):
            raise DependencyException(Errors.bit_range_to_settings.message, self)
        self._set_referenced_setting(referenced_setting_ref)

    # default method for get and switch dependency. Set dependency works opposite way
    # so Get dependency overrides this method to work in opposite direction.
    def _set_referenced_setting(self, referenced_setting_ref):
        self.dst_setting_ref = self.owner_setting_ref
        self.dst_container_key = self.owner_key

        self.src_setting_ref = referenced_setting_ref
        self.src_container_key = self.referenced_key

        if self.src_setting_ref:
            self.source_name = self.src_setting_ref.name
        if self.dst_setting_ref:
            self.destination_name = self.dst_setting_ref.name

        if self.get_bit_count() is not None:
            self.source_name += f' [{self.bit_low}:{self.bit_high}]'

    def get_bit_count(self) -> Optional[int]:
        if self.bit_low is not None and self.bit_high is not None:
            return self.bit_high - self.bit_low + 1
        return None

    def is_value_dependency(self):
        return self.target_property == self.Targets.VALUE

    def execute(self, gui_trigger=False) -> List[ComponentPreChangeState]:
        raise DependencyException(f"Not implemented - {type(self)} is abstract and cannot be instantiated", self)

    def set_default_value(self):
        raise DependencyException(f"Not implemented - {type(self)} is abstract and cannot be instantiated", self)

    def inconsistency_warn(self):
        new_value = self.new_value
        if self.dst_setting_ref and self.dst_setting_ref.params.is_value_list() and \
                self.dst_setting_ref.params.is_in_value_list(new_value):
            new_value = self.dst_setting_ref.params.get_key_from_value_list(new_value)
        return f'Warning: inconsistency of input values between "{self.destination_name}" and "{self.source_name}".'\
               + f' "{self.destination_name}" value will be overridden with "{new_value}".'
