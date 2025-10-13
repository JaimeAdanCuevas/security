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
from .ByteArrayComponent import ByteArrayComponent
from ..LibException import ComponentException
from .IComponent import IComponent
from ..LibConfig import LibConfig


class RootComponent(ByteArrayComponent):

    def __init__(self, xml_node, **kwargs):
        IComponent.root_component = self
        super().__init__(xml_node, **kwargs)

    def _parse_children(self, xml_node, **kwargs):
        # Only <settings> node is parsed from xml to prevent parsing <decomposition> node from before
        # overriding <settings> values
        self.children = []
        self.children_by_name = {}

        try:
            settings_node = xml_node.find(LibConfig.settingsTag)
            if settings_node is None and not LibConfig.allowEmptyConfiguration:
                raise ComponentException(f"{LibConfig.settingsTag} node was not found in layout")
            # pylint: disable-next=use-implicit-booleaness-not-len
            if not len(settings_node) and not LibConfig.allowEmptyConfiguration:
                raise ComponentException(f"{LibConfig.settingsTag} node cannot be empty")
            skip_calculates = kwargs.get('skip_calculates', False)
            component = self.componentFactory.create_component(settings_node, skip_calculates=skip_calculates)
            component.parent = self
            self.children.append(component)
            if component.name not in self.children_by_name:
                self.children_by_name[component.name] = component
        except ComponentException as ex:
            self.trace_exception(ex)
