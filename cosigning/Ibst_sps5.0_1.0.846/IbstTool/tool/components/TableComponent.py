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

from .IComponent import IComponent
from ..LibException import ComponentException
from cffi.backend_ctypes import xrange


class TableComponent(IComponent):
    children_allowed = True
    countTag = "count"
    sortTag = "sort"
    indices = None
    count_formula = None
    sort_value = None

    def __init__(self, xml_node, **kwargs):
        self.indices = []
        if self.countTag in xml_node.attrib:
            self.count_formula = xml_node.attrib[self.countTag]
        super().__init__(xml_node, **kwargs)

    def validate(self):
        IComponent.validate(self)

        # Check if 'count' was specified
        if self.children_allowed and not self.count_formula:
            raise ComponentException("Use 'count' attribute to define table size.", self.name)

    def get_count(self):
        return self.calculate_value(self.count_formula, allow_calculate=True)
    
    def sort_indeces(self, xml_node):
        for i in xrange(0, self.get_count()):
            sort_formula = xml_node.attrib[self.sortTag]
            if "{index}" in sort_formula:
                sort_formula = sort_formula.replace("{index}", str(i))
            if "{parent_index}" in sort_formula:
                sort_formula = sort_formula.replace("{parent_index}", str(self.get_table_index()))
            sort_value = self.calculate_value(sort_formula, allow_calculate=True)
            self.indices.append((i, sort_value))
        if self.indices:
            self.indices.sort(key=lambda x: x[1])

    def parse_children(self, xml_node, buffer=None):
        self.children = []
        self.children_by_name = {}
        if self.sortTag in xml_node.attrib:
            self.sort_indeces(xml_node)
        try:
            for child_node in xml_node:
                if self.indices:
                    for indices in self.indices:
                        self.componentFactory.create_component(child_node, buffer=buffer, index=indices[0], parent=self)
                else:
                    for i in xrange(self.get_count()):
                        self.componentFactory.create_component(child_node, buffer=buffer, index=i, parent=self)

        except ComponentException as ex:
            self.trace_exception(ex)
            
    def _get_bytes(self):
        return self.value
