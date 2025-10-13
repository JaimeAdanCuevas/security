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


class GetDependency(Dependency):
    tag = Dependency.Tags.getTag

    def execute(self):
        if self.setting_property is None:
            self.src_setting_ref.copy_to(self.dst_setting_ref)
        else:
            new_value = self.src_setting_ref.get_property(self.setting_property)
            bit_count = self.get_bit_count()
            if bit_count is not None:
                mask = ((1 << bit_count) - 1) << self.bit_low
                new_value = (mask & new_value) >> self.bit_low
            self.dst_setting_ref._set_value(new_value)

