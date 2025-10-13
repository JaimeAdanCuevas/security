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
from mmap import ACCESS_READ
from ..structures import Buffer
from .ByteArrayComponent import ByteArrayComponent
from ..LibException import LibException, ComponentException
from ..utils import validate_file
from .IComponent import IComponent
from ..LibConfig import LibConfig
from .DecompositionComponent import DecompositionComponent


class RootComponent(ByteArrayComponent):

    def __init__(self, xml_node, **kwargs):
        IComponent.rootComponent = self
        super().__init__(xml_node, **kwargs)

    def parse_children(self, xml_node, buffer=None):
        self.children = []
        self.children_by_name = {}

        if not self.is_gui:
            nodes_list = [LibConfig.settingsTag, DecompositionComponent.decompositionTag, 'layout']
        else:
            nodes_list = [LibConfig.settingsTag, DecompositionComponent.decompositionTag]
        try:
            for node_name in nodes_list:
                node = xml_node.find(node_name)
                if node is None and node_name != DecompositionComponent.decompositionTag:
                    raise LibException("Invalid configuration file: missing '{}' node"
                                       .format(node_name))
                elif node is None and node_name == DecompositionComponent.decompositionTag:
                    continue

                component = self.componentFactory.create_component(node)
                component.parent = self
                self.children.append(component)
                if component.name not in self.children_by_name:
                    self.children_by_name[component.name] = component
        except ComponentException as ex:
            self.trace_exception(ex)
