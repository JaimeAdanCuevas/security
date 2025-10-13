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
from .IComponent import IComponent
from ..LibException import ComponentException


class SeparatorComponent(IComponent):
    id = 0

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        SeparatorComponent.id += 1
        self.name = f'separator_{SeparatorComponent.id}'

    def build_layout(self, buffer, clear_build_settings: bool = False):
        raise ComponentException('Trying to build GUI only element', self.node_tag)

    def build(self, buffer):
        raise ComponentException('Trying to build GUI only element', self.node_tag)

    def to_xml_node(self, parent, simple_xml: bool, save_user_notes=True):
        pass

    def is_node_overridable(self):
        return False
