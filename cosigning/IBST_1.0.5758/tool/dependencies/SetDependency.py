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

from ..ColorPrint import log
from ..PropertyState import PropertyState, ComponentPreChangeState
from .Dependency import Dependency
from ..LibException import DependencyException, ComponentException, InvalidDuplicateRangeException


class SetDependency(Dependency):
    tag = Dependency.Tags.SET

    def execute(self, gui_trigger=False) -> List[ComponentPreChangeState]:
        """
        Execute Set dependency.
        :param gui_trigger: Flag determining if call came from GUI or CLI
        :return: List[Tuple[IComponent, Set[PropertyState]]]; Dependency execution result.
        """
        allowed_targets = [self.Targets.VALUE.value, self.Targets.ENABLED.value, self.Targets.VISIBLE.value,
                           self.Targets.XML_SAVE.value]
        allowed_targets_string = "' or '".join(allowed_targets)
        if self.setting_property is None or (self.setting_property not in allowed_targets and
                                             (self.src_setting_ref.component_type != 'FileComponent'
                                              or self.setting_property != self.Targets.PATH.value)):
            file_component_message = f"or '{self.Targets.PATH.value}' " \
                if self.src_setting_ref.component_type == 'FileComponent' else ''
            raise DependencyException(f"'{self.tag}' dependency must reference "
                                      f"'{allowed_targets_string}' {file_component_message}"
                                      f"property", self)
        if self.setting_property == self.Targets.ENABLED.value and \
                self.dst_setting_ref.component_type != 'GroupComponent':
            raise DependencyException(f"'{self.tag}' dependency with '{self.Targets.ENABLED.value}"
                                      f"' property must reference GroupComponent", self)

        if self.gui_only and not gui_trigger:
            return []
        if self.calculate is not None:
            new_value = self.src_setting_ref.expr_engine.calculate_value(self.calculate, None, True)
        else:
            new_value = self.src_setting_ref.value
        if new_value is None:
            return []

        if self.src_setting_ref.component_type == 'FileComponent' \
                and self.setting_property == self.Targets.VALUE.value:
            self.setting_property = self.Targets.PATH.value
        old_value = None
        try:
            old_value = self.dst_setting_ref.get_property(self.setting_property)
        except ComponentException:
            pass
        bit_count = self.get_bit_count()

        if self.is_duplicate:
            if not self._value_fits_in_bit_range():
                if self.src_setting_ref.params.is_value_list():
                    printed_value = self.src_setting_ref.get_value_label_from_value_list()
                else:
                    printed_value = self.src_setting_ref.value

                raise InvalidDuplicateRangeException(
                    f"{self.src_setting_ref.display_name}: unable to set value "
                    f"{printed_value}. Value exceeds range of {self.dst_setting_ref.name} "
                    f"[{self.bit_low}:{self.bit_high}]")

        # pylint: disable=duplicate-code
        if not self.source_name:
            self.source_name = self.src_setting_ref.name
        if not self.destination_name:
            self.destination_name = self.dst_setting_ref.name

        if bit_count is not None:
            mask = ((1 << bit_count) - 1) << self.bit_low
            new_value = (~mask & old_value) | ((new_value << self.bit_low) & mask)
        # pylint: enable=duplicate-code

        if old_value != new_value:
            if self.setting_property == self.Targets.ENABLED.value:
                result = self.dst_setting_ref.parse_string_value(str(int(new_value)))
                self.new_value = new_value
                return result
            if self.setting_property == self.Targets.VISIBLE.value:
                self.dst_setting_ref.ui_params.visible = bool(new_value)
            elif self.setting_property == self.Targets.XML_SAVE.value:
                self.dst_setting_ref.xml_save = bool(new_value)
                self.dst_setting_ref.xml_save_formula = str(bool(new_value))
                return [(self.dst_setting_ref, {PropertyState(self.setting_property, old_value),
                                                PropertyState(PropertyState.SupportedProperties.XML_SAVE_FORMULA,
                                                              old_value)})]
            else:
                if self.dst_setting_ref.params.is_value_list():
                    old_value = self.dst_setting_ref.params.get_key_from_value_list(old_value)
                else:
                    old_value = self.dst_setting_ref.get_value_string()

                return_value = self.dst_setting_ref.parse_string_value(str(new_value))

                if self.dst_setting_ref.params.is_value_list():
                    new_value = self.dst_setting_ref.params.get_key_from_value_list(new_value)
                else:
                    new_value = self.dst_setting_ref.get_value_string()

                if self.gui_only and gui_trigger and str(old_value) != str(new_value):
                    log().info(f"Changing setting {self.dst_setting_ref.name} value from {old_value}"
                               f" to {new_value}.", gui_visible=True)
                self.new_value = new_value

                return return_value

            self.new_value = new_value

            return [(self.dst_setting_ref, {PropertyState(self.setting_property, old_value)})]

        return []

    def _set_referenced_setting(self, referenced_setting_ref):
        self.dst_setting_ref = referenced_setting_ref
        self.dst_container_key = self.referenced_key

        self.src_setting_ref = self.owner_setting_ref
        self.src_container_key = self.owner_key

        if self.src_setting_ref:  # pylint: disable=duplicate-code
            self.source_name = self.src_setting_ref.name
        if self.dst_setting_ref:
            self.destination_name = self.dst_setting_ref.name

        if self.get_bit_count() is not None:
            self.destination_name += f' [{self.bit_low}:{self.bit_high}]'

    def _value_fits_in_bit_range(self):
        destination_bit_count = self.get_bit_count()
        source_bit_count = self.src_setting_ref.get_bit_count()\
            if self.src_setting_ref.component_type == 'Bit'\
            else None

        # in case we do not have access to bit count for example number component
        if source_bit_count is None or destination_bit_count is None:
            return True

        if destination_bit_count >= source_bit_count:
            return True

        inserted_value = self.src_setting_ref.value
        max_possible_value = 2 ** destination_bit_count - 1

        return inserted_value <= max_possible_value
