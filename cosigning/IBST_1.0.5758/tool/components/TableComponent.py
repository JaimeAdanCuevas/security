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
from cffi.backend_ctypes import xrange
from .IComponent import IComponent
from ..LibException import ComponentException
from ..utils import MapData


class TableComponent(IComponent):
    """Component used for repeating data with the same structure, 'count' attribute must be provided to tell how many
    entries should the table produce. There is also a special component property 'index' that can be used in table
    children in order to get index of currently iterated entry. For example:

    ```xml
    <table name="some_modules" count="3" >
       <byte_array name="module">
          <number name="module_index" size="4" calculate="this.index" />
          <byte_array name="some_data" size="64" value="0" />
       </byte_array>
    </table>
    ```

    Table component can refer to iterable component values by using some specific index or the index of current entry.
    *Indices* attribute needs to be set to chosen iterable indices property in order for it to work.
    Let's refer to iterable from iterable component description example for this:

    ```xml
    <table name="some_modules" count="/settings/images.size" indices="/settings/images.indices" >
       <byte_array name="iterable_images">
          <byte_array name="data" calculate="/settings/images[{index}]/image.data" />
          <string name="image_type" size="6" calculate="/settings/images[{index}]/type.value" />
          <number name="image_id" size="4" calculate="/settings/images[{index}]/id.value" />
       </byte_array>
    </table>
    ```

    It's possible to use *sort* attribute instead of *indices* in order to provide a value by which the indexes
    will be sorted from lowest to highest. In the following example, table elements will appear in the binary
    in the order dependent by 'id' component from settings, element with the lowest id will appear first:

    ```xml
    <table name="some_modules" count="/settings/images.size" sort="/settings/images[{index}]/id.value">
       <byte_array name="iterable_images">
          <byte_array name="data" calculate="/settings/images[{index}]/image.data" />
          <string name="image_type" size="6" calculate="/settings/images[{index}]/type.value" />
          <number name="image_id" size="4" calculate="/settings/images[{index}]/id.value" />
       </byte_array>
    </table>
    ```
    """

    class Tags(IComponent.Tags):
        COUNT = "count"
        COUNT_POINTER = "count_pointer"  # count_pointer helps with decomposition and isn't used in building
        SORT = "sort"
        INDICES = "indices"

    children_allowed = True
    indices = None
    count_formula = None
    count_pointer_formula = None
    sort_value = None

    def __init__(self, xml_node, **kwargs):
        self.indices = []
        if self.Tags.COUNT in xml_node.attrib:
            self.count_formula = xml_node.attrib[self.Tags.COUNT]
        if self.Tags.COUNT_POINTER in xml_node.attrib:
            self.count_pointer_formula = xml_node.attrib[self.Tags.COUNT_POINTER]
        super().__init__(xml_node, **kwargs)

    def get_count(self):
        count = self.calculate_value(self.count_formula, allow_calculate=True)
        if isinstance(count, (bytes, bytearray)):
            return int.from_bytes(count, "little")
        return count

    def parse_indices(self, indices_formula):
        indices = self.calculate_value(indices_formula, allow_calculate=True)
        if not isinstance(indices, list):
            raise ComponentException(f"Indices attribute should be a list of indices, instead {indices} received",
                                     self.name)
        self.indices = [(index, None) for index in indices]

    def sort_indices(self, xml_node):
        for i in xrange(0, self.get_count()):
            sort_formula = xml_node.attrib[self.Tags.SORT]
            if "{index}" in sort_formula:
                sort_formula = sort_formula.replace("{index}", str(i))
            if "{parent_index}" in sort_formula:
                sort_formula = sort_formula.replace("{parent_index}", str(self.get_table_index()))
            sort_value = self.calculate_value(sort_formula, allow_calculate=True)
            self.indices.append((i, sort_value))
        if self.indices:
            self.indices.sort(key=lambda x: x[1])

    def _parse_children(self, xml_node, **kwargs):
        self.children = []
        self.children_by_name = {}
        if self.Tags.SORT in xml_node.attrib and not self._skip_calculates:
            self.sort_indices(xml_node)
        if self.Tags.INDICES in xml_node.attrib and not self._skip_calculates:
            self.parse_indices(xml_node.attrib[self.Tags.INDICES])
        try:
            kwargs['parent'] = self
            for child_node in xml_node:
                if self._skip_calculates:
                    self.componentFactory.create_component(child_node, **kwargs)
                elif self.indices:
                    for indices in self.indices:
                        self.componentFactory.create_component(child_node, index=indices[0], **kwargs)
                else:
                    for i in xrange(self.get_count()):
                        self.componentFactory.create_component(child_node, index=i, **kwargs)

        except ComponentException as ex:
            self.trace_exception(ex)

    def _get_bytes(self):
        return self.value

    def _set_map_names_table_component(self):
        for children in self.children:
            if children.map_name and "/" in children.map_name:
                try:
                    calculated_val = children.expr_engine.calculate_value(formula=children.map_name,
                                                                          allow_none_return=True)
                except ComponentException:
                    calculated_val = None
                children.map_name = calculated_val

    @property
    def map_data(self) -> [MapData]:
        """Returns list of start offset, length, intent, area name"""
        self._set_map_names_table_component()
        return super().map_data
