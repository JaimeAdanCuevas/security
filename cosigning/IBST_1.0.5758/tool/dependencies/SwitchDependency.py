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
from typing import List

from .Dependency import Dependency
from ..LibException import DependencyException
from ..PropertyState import PropertyState, ComponentPreChangeState


class SwitchDependency(Dependency):
    tag = Dependency.Tags.SWITCH

    def _parse_properties_dict(self, properties):
        if self.Tags.SOURCE not in properties:
            raise DependencyException(f"{self.Tags.SOURCE} entry missing", self)

        if self.Tags.VALUE_LIST not in properties:
            raise DependencyException(f"{self.Tags.VALUE_LIST} entry missing", self)

        self._parse_referenced_setting_path(properties[self.Tags.SOURCE])
        self.value_list = properties[self.Tags.VALUE_LIST]

    def execute(self, gui_trigger=False) -> List[ComponentPreChangeState]:
        """
        Execute Switch dependency.
        :param gui_trigger: Flag determining if call came from GUI or CLI
        :return: List[Tuple[IComponent, Set[PropertyState]]]; Dependency execution result.
        """
        changed = []
        new_value = self.src_setting_ref.get_property(self.setting_property)
        if str(new_value) in self.value_list:
            new_value = self.value_list[str(new_value)]
        elif self.Tags.DEFAULT in self.value_list:
            new_value = self.value_list[self.Tags.DEFAULT]
        else:
            raise DependencyException(f"Default value missing in value list: {self.value_list}", self)
        old_value = self.dst_setting_ref.value
        self.dst_setting_ref.parse_string_value(new_value)
        self.new_value = new_value
        if self.dst_setting_ref.value != old_value:
            changed.append((self.dst_setting_ref, {PropertyState(PropertyState.SupportedProperties.VALUE, old_value)}))

        return changed

    def set_default_value(self):
        new_value = self.src_setting_ref.get_property(self.setting_property)
        if str(new_value) in self.value_list:
            self.dst_setting_ref.default_value = self.dst_setting_ref. \
                get_parsed_string_value(self.value_list[str(new_value)])
        elif self.Tags.DEFAULT in self.value_list:
            self.dst_setting_ref.default_value = self.dst_setting_ref. \
                get_parsed_string_value(self.value_list[self.Tags.DEFAULT])
        else:
            raise DependencyException(f"Default value missing in value list: {self.value_list}", self)
