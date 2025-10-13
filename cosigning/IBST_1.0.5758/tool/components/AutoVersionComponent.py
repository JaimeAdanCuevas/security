#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2020-2022 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

from distutils.version import LooseVersion

from .IComponent import IComponent
from .NumberComponent import NumberComponent
from .StringComponent import StringComponent
from ..LibException import ComponentException


class AutoVersionComponent(IComponent):
    VER_SEPARATOR = '.'

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.version_format = None
        if self.children:
            children_formats = [f"{'string' if isinstance(p, StringComponent) else 'number'}[{p.size}"
                                f" {'bytes' if p.size > 1 else 'byte'}]" for p in self.children]
            self.version_format = '.'.join(children_formats)
            self._check_value_by_children(self.value)

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        child: IComponent
        for child in self.children:
            child.ui_params.read_only = True
            if not isinstance(child, StringComponent) and not isinstance(child, NumberComponent):
                raise ComponentException(f"'{self.node_tag}' component can have only 'number' or 'string' children. "
                                         f"'{child.node_tag}' children is forbidden")

    def get_parsed_string_value(self, value):
        loose_ver_val = LooseVersion(value)
        if self.children:
            self._check_value_by_children(loose_ver_val)
        return loose_ver_val

    def _check_value_by_children(self, loose_ver_val):
        str_val = loose_ver_val.vstring
        wrong_version_format_exception = ComponentException(
            f"Invalid value: '{str_val}', should be string in version format: {self.version_format}")
        parts = str_val.split(AutoVersionComponent.VER_SEPARATOR)
        if len(parts) != len(self.children):
            raise wrong_version_format_exception
        for val, child in list(zip(parts, self.children)):
            try:
                child.parse_string_value(val)
                child.get_bytes()
            except ComponentException:
                raise wrong_version_format_exception
