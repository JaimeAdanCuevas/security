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

from ..utils import parse_json_str
from ..LibException import DependencyException
from ..UniqueKey import UniqueKey, VersionedName
from ..LibConfig import LibConfig


class Dependency:
    tag = None
    value_list = None
    bit_low = None
    bit_high = None
    src_setting_ref = None
    dst_setting_ref = None
    referenced_set_name = None
    setting_property = None
    unique_key = None

    class Tags:
        getTag = "get"
        switchTag = "switch"
        setTag = "set"
        pathTag = "path"
        bitLowTag = "bit_low"
        bitHighTag = "bit_high"
        sourceTag = "source"
        valueListTag = "value_list"
        defaultTag = "default"

    def __init__(self, properties, owner_setting_ref, is_duplicate=False):
        self.owner_setting_ref = owner_setting_ref
        self.is_duplicate = is_duplicate

        # If 'properties' is of type str then assume that it's simply a path to some other setting
        if isinstance(properties, str):
            self._parse_referenced_setting_path(properties)
        elif isinstance(properties, dict):
            self._parse_properties_dict(properties)
        else:
            raise DependencyException(f"Unsupported type of dependency properties: {type(properties).__name__} "
                                      f"for dependency: {self.tag}", self)

    def _parse_referenced_setting_path(self, path):
        if not path.strip():
            raise DependencyException(f"Specified dependency path cannot be empty, in dependency: {self.tag}", self)
        parts = path.split(LibConfig.pathSeparator)
        self.referenced_set_name, self.setting_property, self.unique_key = self._parse_dependency_path(parts)

    def _parse_dependency_path(self, parts):
        plug_key = VersionedName()
        cont_key = VersionedName()

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

    def _parse_properties_dict(self, properties):
        if self.Tags.pathTag not in properties:
            raise DependencyException(f"{self.Tags.pathTag} is missing from dependency: {self.tag}", self)
        self._parse_referenced_setting_path(properties[self.Tags.pathTag])
        if self.Tags.bitLowTag in properties or self.Tags.bitHighTag in properties:
            if self.Tags.bitLowTag not in properties or self.Tags.bitHighTag not in properties:
                raise DependencyException(f"Both {self.Tags.bitLowTag} and {self.Tags.bitHighTag} must be specified if "
                                          f"at least one of them is given", self)
            self.bit_low = properties[self.Tags.bitLowTag]
            self.bit_high = properties[self.Tags.bitHighTag]

            if self.bit_low > self.bit_high:
                raise DependencyException(f"{self.Tags.bitLowTag} cannot be greater then {self.Tags.bitHighTag}", self)

    def set_referenced_setting(self, referenced_setting_ref):
        if self.get_bit_count() and (not isinstance(referenced_setting_ref.get_default_value(), int) or
                                     not isinstance(self.owner_setting_ref.get_default_value(), int)):
            raise DependencyException("Bit range can be applied only to numbers", self)
        self._set_referenced_setting(referenced_setting_ref)

    def _set_referenced_setting(self, referenced_setting_ref):
        self.dst_setting_ref = self.owner_setting_ref
        self.src_setting_ref = referenced_setting_ref

    def get_bit_count(self) -> (int, None):
        if self.bit_low is not None and self.bit_high is not None:
            return self.bit_high - self.bit_low + 1
        return None

    def execute(self):
        raise DependencyException(f"Not implemented - {type(self)} is abstract and cannot be instantiated", self)

    def set_default_value(self):
        raise DependencyException(f"Not implemented - {type(self)} is abstract and cannot be instantiated", self)

    @staticmethod
    def get_bits_name(setting_ref):
        if setting_ref.has_dependencies():
            try:
                dependency_dict = parse_json_str(setting_ref.dependency_formula)[0]['get']
                source = dependency_dict['path']
                if source.endswith('.value'):
                    return '{} [{}:{}]'.format(source[:-6], dependency_dict['bit_low'], dependency_dict['bit_high'])
            except (IndexError, KeyError, TypeError):
                return None
        return None

    def inconsistency_warn(self):
        return f'Warning: inconsistency of input values. "{self.destination_name}" will be overwritten by "{self.source_name}".'
