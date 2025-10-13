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

from ..AttributeGroup import GroupUiParams
from ..ColorPrint import log
from ..Converter import Converter
from .ByteArrayComponent import ByteArrayComponent
from .IComponent import IComponent
from ..LibConfig import LibConfig
from ..LibException import ComponentException
from ..PropertyState import PropertyState, ComponentPreChangeState


class GroupComponent(ByteArrayComponent):
    default_enabled_formula = ""

    ui_params_class = GroupUiParams

    def __init__(self, xml_node, **kwargs):
        self._visible = True
        super().__init__(xml_node, **kwargs)
        self.enabled_by_default = self._parse_enabled() if self.enabled_formula else True
        self.enabled = self.enabled_by_default

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        old_enabled_value = self.enabled_formula
        old_enabled_property = PropertyState(PropertyState.SupportedProperties.ENABLED, self.enabled)
        old_enabled_formula_property = PropertyState(PropertyState.SupportedProperties.ENABLED_FORMULA,
                                                     self.enabled_formula)
        new_enabled_value = bool(Converter.string_to_int(value))
        self.enabled = new_enabled_value
        self.enabled_formula = str(new_enabled_value)

        modified_settings = [(self, {old_enabled_property, old_enabled_formula_property})] if \
            old_enabled_value != self.enabled_formula \
            else []
        if modified_settings:
            # if parent was disabled all the children should be disabled
            if not new_enabled_value:
                for subgroup in [child for child in self.children
                                 if child.node_tag == IComponent.Tags.GROUP and child.enabled_formula]:
                    modified_settings.extend(subgroup.parse_string_value(value))
            # if one child is enabled parent should be also enabled
            elif isinstance(self.parent, GroupComponent) and self.parent.enabled_formula:
                if self.parent.enabled_formula != self.enabled_formula and \
                        (LibConfig.isLoadingUserXml or not LibConfig.isGui):
                    log().warning(f"'{self.parent.name}' file will be enabled because child "
                                       f"'{self.name}' is enabled")
                modified_settings.extend(self.parent.parse_string_value(value))

        return modified_settings

    def _should_omit_parsing(self, xml_node):
        super()._should_omit_parsing(xml_node)
        return False

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self.default_enabled_formula = self._parse_attribute(xml_node, self.Tags.ENABLED, False, None)

    @property
    def has_non_default_value(self):
        if self.enablable:
            if not self.exists:
                return self.enabled_by_default != self.is_enabled()
            return self.enabled_by_default != self.enabled
        return False
