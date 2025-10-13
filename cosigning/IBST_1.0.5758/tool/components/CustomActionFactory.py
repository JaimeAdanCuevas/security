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

from library.tool.components.CustomActionComponent import CustomActionComponent
from library.tool.components.ComponentFactory import ComponentFactory


class CustomActionFactory(ComponentFactory):
    def __init__(self, xml_node):
        super().__init__()
        self._class_map[CustomActionComponent.nodeName] = CustomActionComponent
        self.xml_node = xml_node
        self.root_component = self.create_root_component(self.xml_node)
