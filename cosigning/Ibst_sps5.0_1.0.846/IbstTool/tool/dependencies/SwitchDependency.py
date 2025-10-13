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

from .Dependency import Dependency
from ..LibException import DependencyException


class SwitchDependency(Dependency):
    tag = Dependency.Tags.switchTag

    def _parse_properties_dict(self, properties):
        if self.Tags.sourceTag not in properties:
            raise DependencyException(f"{self.Tags.sourceTag} entry missing", self)

        if self.Tags.valueListTag not in properties:
            raise DependencyException(f"{self.Tags.valueListTag} entry missing", self)

        self._parse_referenced_setting_path(properties[self.Tags.sourceTag])
        self.value_list = properties[self.Tags.valueListTag]

    def execute(self):
        changed = []
        new_value = self.src_setting_ref.get_property(self.setting_property)
        if str(new_value) in self.value_list:
            new_value = self.value_list[str(new_value)]
        elif self.Tags.defaultTag in self.value_list:
            new_value = self.value_list[self.Tags.defaultTag]
        else:
            raise DependencyException(f"Default value missing in value list: {self.value_list}", self)
        temp_ref_value = self.dst_setting_ref.value
        self.dst_setting_ref.parse_string_value(new_value)
        if self.dst_setting_ref.value != temp_ref_value:
            changed.append(self.dst_setting_ref)
        return changed

    def set_default_value(self):
        new_value = self.src_setting_ref.get_property(self.setting_property)
        if str(new_value) in self.value_list:
            self.dst_setting_ref.default_value = self.dst_setting_ref.\
                                                _parse_string_value(self.value_list[str(new_value)])
        elif self.Tags.defaultTag in self.value_list:
            self.dst_setting_ref.default_value = self.dst_setting_ref.\
                                                _parse_string_value(self.value_list[self.Tags.defaultTag])
        else:
            raise DependencyException(f"Default value missing in value list: {self.value_list}", self)

