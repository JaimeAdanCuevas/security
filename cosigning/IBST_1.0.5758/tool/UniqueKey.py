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

from packaging.version import Version
from .Errors import Errors
from .LibException import MergeException

VER_NAME_SEP = ':'
UNIQUE_SEP = '/'


class VersionedName:
    def __init__(self, name='', version='', name_ver='', separator=VER_NAME_SEP):
        self.name = ''
        self.version = '0.0'
        self.strict_ver = Version('0.0')
        self.separator = separator
        if name_ver:
            splitted = name_ver.split(separator)
            name = splitted[0]
            if len(splitted) == 2:
                version = splitted[1]
        if name:
            self.name = name
        if version:
            self.version = version
        if self.version:
            self._parse_version()

    def get_versioned_name(self):
        return self.get_versioned_name_sep(self.separator)

    def get_versioned_name_sep(self, separator):
        if self.has_name_ver():
            return self.concat(self.name, self.version, separator)
        else:
            return self.name

    @staticmethod
    def concat(name, version, separator=VER_NAME_SEP):
        return name + separator + version

    def is_empty(self):
        return not self.name

    def has_name_ver(self):
        return self.name and self.version != "0.0"

    def __str__(self):
        return self.get_versioned_name()

    def to_format_str(self):
        if self.has_name_ver():
            return f"{self.name} v. {self.version}"
        else:
            return self.name

    def _parse_version(self):
        try:
            self.strict_ver = self._parse_match_version(self.version)
        except (ValueError, TypeError) as e:
            raise MergeException(Errors.wrong_container_version.message.format(version=self.version,
                                                                               container_name=self.name)) from e

    @staticmethod
    def _parse_match_version(version):
        version_regex = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$', re.VERBOSE | re.ASCII)
        match = version_regex.match(version)
        if not match:
            raise ValueError(f'invalid version number {version}')
        major, minor, patch, prerelease, prerelease_num = match.group(1, 2, 4, 5, 6)
        parsed_ver = ".".join([elem for elem in [major, minor, patch, prerelease, prerelease_num] if elem is not None])
        return parsed_ver

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               self.name == other.name and \
               self.version == other.version

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))


class UniqueKey:
    def __init__(self, cont_key: VersionedName, plug_key: VersionedName = VersionedName()):
        self.cont_key = cont_key
        self.plug_key = plug_key

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               self.cont_key == other.cont_key and \
               self.plug_key == other.plug_key

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        if self.has_plugin_name():
            return self.concat(self.cont_key, self.plug_key)
        else:
            return f"{str(self.cont_key)}"

    def __hash__(self):
        h = hash(self.cont_key) ^ hash(self.plug_key)
        return h

    def __iter__(self):
        return iter(str(self.cont_key) + str(self.plug_key))

    def has_plugin_name(self):
        return not self.plug_key.is_empty()

    def update(self, other):
        self.cont_key = other.cont_key
        self.plug_key = other.plug_key

    def to_format_str(self):
        if self.has_plugin_name():
            return f"{self.cont_key.to_format_str()} in plugin: {self.plug_key.to_format_str()}"
        else:
            return self.cont_key.to_format_str()

    def is_empty(self):
        return self.cont_key.is_empty() and self.plug_key.is_empty()

    @staticmethod
    def concat(cont_key, plug_key):
        return str(cont_key) + UNIQUE_SEP + str(plug_key)

    @staticmethod
    def from_str(name):
        versions = name.split(UNIQUE_SEP)
        plug_key = VersionedName()
        if len(versions) == 1:
            cont_key = VersionedName(name_ver=versions[0])
        elif len(versions) == 2:
            cont_key = VersionedName(name_ver=versions[0])
            plug_key = VersionedName(name_ver=versions[1])
        else:
            raise MergeException(Errors.wrong_container_name.message.format(container_name=name))
        return UniqueKey(cont_key, plug_key)
