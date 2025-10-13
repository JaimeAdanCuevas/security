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

import re

from .LibException import ComponentException, LibException
from .Converter import Converter
from .utils import last_index, bin_operators_map
from .LibConfig import LibConfig


class ExpressionEngine:
    def __init__(self, component):
        self.component = component

    def calculate_value(self, formula=None, parts=None, allow_calculate=False, allow_none_return=False,
                        build_process=False):
        if parts is None:
            parts = list(filter(None, formula.split(" ")))

        if any('.data[' in s for s in parts) or any('.value[' in s for s in parts):
            self._convert_paths_in_data_range_to_numbers(parts)

        if any('(' in s for s in parts) or any(')' in s for s in parts):
            return self.calculate_with_brackets(parts)
        elif parts.count(':') > 0 or parts.count('?') > 0:
            return self.calculate_with_ifs(parts, allow_calculate, build_process)

        if not parts:
            raise ComponentException("Invalid formula", self.component.name)
        elif len(parts) == 1:
            return self.get_value_of_variable(parts[0], allow_calculate, allow_none_return, build_process)
        else:
            return self.get_value_of_expression(parts, allow_calculate)

    def _convert_paths_in_data_range_to_numbers(self, parts: list) -> None:
        """
        Converts data range formula parts to a format, where each part of a formula is split by a path split character.
        For an example, calculate formula: '/settings/component.data[parent/start_offset.value:parent/end_offset.value]'
        is converted to a format '/settings/component.data[0:1]'.
        :param parts: Parts of a calculated formula split by space character.
        """
        for index, element in enumerate(parts):
            nested_calculate_formula_regex = r"((?<=\.data\[)|(?<=\.value\[))(.*):(.*)(?=\])"
            data_range_result = re.search(nested_calculate_formula_regex, element)
            if data_range_result:
                data_range_text = data_range_result.group(0)
                colon_index = data_range_text.index(':')
                data_range_start = data_range_text[:colon_index]
                parts[index] = parts[index].replace(data_range_start, str(self.calculate_value(data_range_start)))
                if data_range_text[-1] != ':':
                    data_range_end = data_range_text[colon_index + 1:]
                    parts[index] = parts[index].replace(data_range_end, str(self.calculate_value(data_range_end)))

    def get_value_of_variable(self, variable: str, allow_calculate, allow_none_return=False, build_process=False):
        value = self.value_from_string(variable)
        if variable.find("unique[") != -1:
            return self.is_variable_not_unique(variable)
        if value is not None:
            return value
        value = self.calculate_value_from_path(variable, allow_calculate, build_process)

        if value is None and not allow_none_return:
            raise ComponentException(f"Expression '{variable}' returns no value.", self.component.name)
        return value

    def value_from_string(self, variable: str):
        if '{index}' in variable:
            variable = variable.replace('{index}', str(self.component.get_table_index()))
        if '{parent_index}' in variable:
            variable = variable.replace('{parent_index}', str(self.component.get_parent_table_index()))
        try:
            return Converter.string_to_bool(variable)
        except ValueError:
            pass
        try:
            return Converter.string_to_int(variable)
        except LibException:
            pass
        try:
            return Converter.inner_string(variable)
        except LibException:
            pass
        return None

    def get_value_of_expression(self, parts, allow_calculate):
        # pylint: disable=unnecessary-lambda-assignment
        left = lambda idx: self.calculate_value(parts=parts[:idx], allow_calculate=allow_calculate)
        right = lambda idx: self.calculate_value(parts=parts[idx + 1:], allow_calculate=allow_calculate)
        # pylint: enable=unnecessary-lambda-assignment
        i = None
        for oper, pair in bin_operators_map.items():
            try:
                if pair[1]:
                    i = last_index(parts, oper)
                else:
                    i = parts.index(oper)
            except ValueError:
                pass
            if i is not None:
                if oper == 'and':
                    return left(i) and right(i)
                elif oper == 'or':
                    return left(i) or right(i)
                elif oper == 'not':
                    return not right(i)
                left_value = left(i)
                right_value = right(i)
                if isinstance(left_value, (bytes, bytearray)) and isinstance(right_value, int):
                    left_value = int.from_bytes(left_value, "big")
                if isinstance(left_value, int) and isinstance(right_value, (bytes, bytearray)):
                    right_value = int.from_bytes(right_value, "big")
                if isinstance(left_value, (bytes, bytearray)) and isinstance(right_value, str):
                    left_value = left_value.decode('utf-8')
                if isinstance(left_value, str) and isinstance(right_value, (bytes, bytearray)):
                    right_value = right_value.decode('utf-8')
                return pair[0](left_value, right_value)

        raise ComponentException(f"Invalid calculation formula: '{' '.join(parts)}'", self.component.name)

    def split_brackets(self, temp_parts):
        parts = []
        for part in temp_parts:
            left_cnt = part.count('(')
            right_cnt = part.count(')')
            parts.extend(['('] * left_cnt)
            if right_cnt == 0:               # here we change '(value)' into '(', 'value', ')' [could be ((value)) etc.]
                parts.append(part[left_cnt:])   # we need to unhook number of '(' from left and ')' for right
            else:                               # there is exception if there is no ')' then we can't unhook from right
                parts.append(part[left_cnt:-1 * right_cnt])  # the raise of exception is lower in this method.
            parts.extend([')'] * right_cnt)
        if parts.count('(') != parts.count(')'):
            raise ComponentException("Invalid formula, number of '(' and ')' must be equal", self.component.name)
        parts = list(filter(None, parts))
        return parts

    # pylint: disable-next=inconsistent-return-statements
    def calculate_with_brackets(self, temp_parts):
        parts = self.split_brackets(temp_parts)
        while len(parts) > 0:
            # Here we are sure that number of '(' and ')' are equal, so if there is no ')'
            # we can calculate value of pure sentence
            if parts.count(')') > 0:
                close_idx = parts.index(')')
            else:
                return self.calculate_value(parts=parts)
            try:
                # but if there is ')' we need to find the closest '(' to the left of it:
                open_idx = len(parts[:close_idx]) - list(reversed(parts[:close_idx])).index('(') - 1
            except ValueError as e:
                raise ComponentException("Invalid formula, '(' must be before ')'", self.component.name) from e
            # and calculate sentence between them as a pure sentence, and replace it with a value
            val = self.calculate_value(parts=parts[open_idx + 1:close_idx])
            parts = parts[:open_idx] + parts[close_idx + 1:]
            parts.insert(open_idx, str(val))
            # we do it recursively until all brackets are calculated

    def calculate_with_ifs(self, parts, allow_calculate, build_process=False):
        try:
            question_mark_idx = parts.index("?")
            colon_idx = parts.index(":")
        except ValueError as e:
            raise ComponentException("Invalid formula, missing ':' / '?' operator required by '?' / ':'",
                                     self.component.name) from e
        if colon_idx < question_mark_idx:
            raise ComponentException("Invalid formula, ':' must be behind '?'", self.component.name)

        if self.calculate_value(parts=parts[:question_mark_idx]):
            return self.calculate_value(parts=parts[question_mark_idx + 1:colon_idx], allow_calculate=allow_calculate,
                                        build_process=build_process)
        return self.calculate_value(parts=parts[colon_idx + 1:], allow_calculate=allow_calculate,
                                    build_process=build_process)

    def calculate_component_from_path(self, formula: str):
        return self.calculate_value_from_path(formula.rsplit('.', 1)[0])

    def calculate_value_from_path(self, path, allow_calculate=False, build_process=False):
        parts = path.split(LibConfig.pathSeparator)

        component = self.component
        for (i, part) in enumerate(parts):
            if not part and i == 0:
                component = self.component.root_component
                continue
            if part and LibConfig.isOrchestrator:
                component = self.component.root_component.get_child(part)
                continue

            if not part:
                raise ComponentException(f"Empty part at index {i} in path '{path}'", self.component.name)
            if i == (len(parts) - 1):
                subparts = part.rsplit(".", maxsplit=1)
            else:
                subparts = [part]

            if subparts[0] == "parent":
                component = component.parent
            elif subparts[0] != "this":
                brackets = re.search(r'(.*)\[(.*)\]', subparts[0])
                if brackets:
                    component = component.get_child(brackets[1])
                if "{index}" in subparts[0]:
                    index = self.component.get_table_index()
                    subparts[0] = subparts[0].replace("{index}", str(index))
                if "{parent_index}" in subparts[0]:
                    index = self.component.get_parent_table_index()
                    subparts[0] = subparts[0].replace("{parent_index}", str(index))
                # TableEntryComponent in calculate formula should be resolved only for decomposition purpose
                if component.component_type == 'TableEntryComponent' and component.is_decomposition_node:
                    component = component.find_table_entry(component.table, False)
                    if component is None:
                        return None
                component = component.get_child(subparts[0])

            if len(subparts) > 1:
                return component.get_property(subparts[1], allow_calculate, build_process)

        return component

    def is_variable_not_unique(self, variable):
        component_value = self.component.get_value_string()
        # 0xff (acceptable only for non-PMBus devices)
        # means that device is disabled and we should not check it uniqueness.
        if component_value == "0xff" or not self.component.parent.enabled:
            return False
        shared_settings = [setting for setting in self.component.root_component.descendants if setting.validate_formula
                           and variable in setting.validate_formula and setting.name != self.component.name and
                           setting.parent.is_enabled()]

        return any(setting.get_value_string() == component_value for setting in shared_settings)
