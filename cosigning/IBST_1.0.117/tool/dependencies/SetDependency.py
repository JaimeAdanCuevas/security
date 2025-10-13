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


class SetDependency(Dependency):
    tag = Dependency.Tags.setTag

    def _set_referenced_setting(self, referenced_setting_ref):
        self.dst_setting_ref = referenced_setting_ref
        self.src_setting_ref = self.owner_setting_ref

    def execute(self):
        if self.setting_property is None or self.setting_property != self.owner_setting_ref.valueTag:
            raise DependencyException(f"'{self.tag}' dependency must reference "
                                      f"'{self.owner_setting_ref.ComponentProperty.Value.value}' property", self)
        else:
            new_value = self.src_setting_ref.value
            bit_count = self.get_bit_count()
            if bit_count is not None:
                mask = ((1 << bit_count) - 1) << self.bit_low
                old_value = self.dst_setting_ref.get_property(self.setting_property)
                new_value = (~mask & old_value) | ((new_value << self.bit_low) & mask)
            self.dst_setting_ref._set_value(new_value)

