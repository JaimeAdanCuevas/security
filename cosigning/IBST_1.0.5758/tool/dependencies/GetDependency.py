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

from ..LibException import ComponentException
from ..PropertyState import PropertyState, ComponentPreChangeState
from ..LibException import DependencyException
from .Dependency import Dependency


class GetDependency(Dependency):
    tag = Dependency.Tags.GET

    def execute(self, gui_trigger=False) -> List[ComponentPreChangeState]:
        """
        Execute Get dependency.
        :param gui_trigger: Flag determining if call came from GUI or CLI
        :return: List[Tuple[IComponent, Set[PropertyState]]]; Dependency execution result.
        """
        if self.gui_only and not gui_trigger:
            return []
        if self.setting_property is None:
            self.src_setting_ref.copy_to(self.dst_setting_ref)
        else:
            if self.calculate is not None:
                new_value = self.src_setting_ref.expr_engine.calculate_value(self.calculate, None, True)
            else:
                new_value = self.src_setting_ref.get_property(self.setting_property)
            old_value = None

            try:
                old_value = self.dst_setting_ref.get_property(self.target_property.value)
            except ComponentException:
                pass

            states = {PropertyState(self.target_property.value, old_value)}
            bit_count = self.get_bit_count()
            # pylint: disable=duplicate-code
            if not self.source_name:
                self.source_name = self.src_setting_ref.name
            if not self.destination_name:
                self.destination_name = self.dst_setting_ref.name

            if bit_count is not None:
                mask = ((1 << bit_count) - 1) << self.bit_low
                new_value = (mask & new_value) >> self.bit_low
            # pylint: enable=duplicate-code
            if old_value != new_value:
                if self.is_value_dependency() or self.setting_property == self.Targets.PATH.value:
                    self.new_value = new_value
                    # pylint: disable-next=import-outside-toplevel
                    from library.tool.components.NumberComponent import NumberComponent
                    if isinstance(new_value, (bytearray, bytes)) and isinstance(self.dst_setting_ref, NumberComponent):
                        str_value = str(int.from_bytes(new_value, self.dst_setting_ref.byte_order))
                        change_state_list = self.dst_setting_ref.parse_string_value(str_value)
                    else:
                        change_state_list = self.dst_setting_ref.parse_string_value(str(new_value))
                    if old_value is None:
                        self.dst_setting_ref.default_value = self.dst_setting_ref.value
                    return change_state_list
                if self.target_property == self.Targets.VALUE_LIST:
                    self.dst_setting_ref.params.dict[self.Targets.VALUE_LIST.value] = new_value
                elif self.target_property == self.Targets.ENABLED:
                    self.dst_setting_ref.enabled = bool(new_value)

                    states.add(PropertyState(PropertyState.SupportedProperties.ENABLED_FORMULA,
                                             self.dst_setting_ref.enabled_formula))
                    self.dst_setting_ref.enabled_formula = str(bool(new_value))
                elif self.target_property == self.Targets.VISIBLE:
                    self.dst_setting_ref.ui_params.visible = bool(new_value)
                elif self.target_property == self.Targets.READ_ONLY:
                    self.dst_setting_ref.ui_params.read_only = bool(new_value)
                elif self.target_property == self.Targets.EXISTS:
                    return self.dst_setting_ref.set_exists(bool(new_value), self.src_setting_ref)
                else:
                    if not hasattr(self.dst_setting_ref, self.target_property.value):
                        raise DependencyException(f"{self.target_property.value} attribute is not supported")
                    setattr(self.dst_setting_ref, self.target_property.value, new_value)

                return [(self.dst_setting_ref, states)]

        return []
