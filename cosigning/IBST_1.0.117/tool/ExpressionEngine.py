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
import operator

from .LibException import ComponentException
from .Converter import Converter
from .utils import last_index
from .LibConfig import LibConfig


class ExpressionEngine:

    bin_operators_map = \
        {  # python operators precedence
            'and': (lambda a, b: a and b, False),
            'or': (lambda a, b: a or b, False),
            '!=': (operator.ne, False),
            '==': (operator.eq, False),
            '>': (operator.gt, False),
            '>=': (operator.ge, False),
            '<=': (operator.le, False),
            '<': (operator.lt, False),
            '^': (operator.xor, True),
            '|': (operator.or_, True),
            '&': (operator.and_, True),
            '<<': (operator.lshift, True),
            '>>': (operator.rshift, True),
            '+': (operator.add, True),
            '-': (operator.sub, True),
            '*': (operator.mul, True),
            '/': (operator.floordiv, True),
            '%': (operator.mod, True),
        }

    def __init__(self, component):
        self.component = component

    def calculate_value(self, formula=None, parts=None, allow_calculate=False):
        # TODO: expression parser with precedence and brackets handling needed
        # TODO: nice to have posibility to watch calculated values, when we have equtation (why it is not equal)

        if parts is None:
            parts = list(filter(None, formula.split(" ")))

        if not parts:
            raise ComponentException("Invalid formula", self.component.name)

        if len(parts) == 1:
            try:
                return Converter.string_to_bool(parts[0])
            except ValueError:
                pass
            try:
                return Converter.string_to_int(parts[0], False)
            except ValueError:
                pass
            if "\'" in parts[0]:
                return parts[0].strip('\'')  # Remove '' for string comparision

            value = self.calculate_value_from_path(parts[0], allow_calculate)

            if value is None:
                raise ComponentException("Expression '{}' returns no value."
                                         .format(parts[0]), self.component.name)
            return value

        i = None
        try:
            i = parts.index("?")
        except ValueError:
            pass
        if i is not None:
            try:
                i2 = parts.index(":")
            except ValueError:
                raise ComponentException("Invalid formula, missing ':' operator required by '?'",
                                         self.component.name)
            if i2 < i:
                raise ComponentException("Invalid formula, ':' must be behind '?'", self.component.name)

            if self.calculate_value(parts=parts[:i]):
                return self.calculate_value(parts=parts[i + 1:i2], allow_calculate=allow_calculate)
            else:
                return self.calculate_value(parts=parts[i2 + 1:], allow_calculate=allow_calculate)

        left = lambda idx: self.calculate_value(parts=parts[:idx], allow_calculate=allow_calculate)
        right = lambda idx: self.calculate_value(parts=parts[idx + 1:], allow_calculate=allow_calculate)

        for oper in self.bin_operators_map.keys():
            pair = self.bin_operators_map[oper]
            try:
                if pair[1]:
                    i = last_index(parts, oper)
                else:
                    i = parts.index(oper)
            except ValueError:
                pass
            if i is not None:
                return pair[0](left(i), right(i))

        raise ComponentException("Invalid calculation formula: '{}'"
                                 .format(" ".join(parts)), self.component.name)

    def calculate_component_from_path(self, formula: str):
        return self.calculate_value_from_path(formula.rsplit('.', 1)[0])

    def calculate_value_from_path(self, path, allow_calculate=False):
        parts = path.split(LibConfig.pathSeparator)

        component = self.component
        for (i, part) in enumerate(parts):
            if not part and i == 0:
                component = self.component.rootComponent
                continue

            if not part:
                raise ComponentException("Empty part at index {} in path '{}'"
                                         .format(i, path), self.component.name)
            if i == (len(parts) - 1):
                subparts = part.rsplit(".", maxsplit=1)
            else:
                subparts = [part]

            if subparts[0] == "parent":
                component = component.parent
            elif subparts[0] != "this":
                if "{index}" in subparts[0]:
                    index = self.component.get_table_index()
                    subparts[0] = subparts[0].replace("{index}", str(index))
                if "{parent_index}" in subparts[0]:
                    index = self.component.get_parent_table_index()
                    subparts[0] = subparts[0].replace("{parent_index}", str(index))
                component = component.get_child(subparts[0])

            if len(subparts) > 1:
                return component.get_property(subparts[1], allow_calculate)

        return component

