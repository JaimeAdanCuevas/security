#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2019 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
from lxml.etree import Element, SubElement
import lxml.etree as etree

from .components.IComponent import IComponent
from .components.TableEntryComponent import TableEntryComponent
from .components.function.UpdateValueFunction import UpdateValueFunction
from .components.BitFieldComponent import BitFieldComponent
from .utils import prepare_string_to_xml


class IMapFormatter:
    mapExt = '.map'

    def __init__(self):
        self._formatted_map = ''

    def _create_header(self):
        raise NotImplementedError()

    def _create_entries(self, parent: IComponent):
        raise NotImplementedError()

    def create_map(self, map_root: IComponent) -> str:
        self._formatted_map = ''
        self._formatted_map += self._create_header()
        self._formatted_map += self._create_entries(map_root)
        return self._formatted_map


class XmlMapFormatter(IMapFormatter):
    mapExt = '.xml'
    attributesDefault = [IComponent.offsetTag, IComponent.sizeTag]
    skipEmpty = True
    maxLevel = 1
    excludingPredicates = [lambda c: isinstance(c, UpdateValueFunction),
                           lambda c: isinstance(c, TableEntryComponent),
                           lambda c: c.calc_only]
    attributesMap = {BitFieldComponent.Bit: [IComponent.valueTag]}
    maxValueSize = 128

    def _create_header(self):
        return ''

    def _create_entries(self, parent: IComponent):
        root = self._create_xml_entry(parent, None)
        return etree.tostring(root, encoding='utf-8', pretty_print=True).decode('utf-8')

    def _create_xml_entry(self, component: IComponent, parent_node, indent=0):
        if any(pred for pred in self.excludingPredicates if pred(component)):
            if isinstance(component, TableEntryComponent):
                return self._create_xml_entry_table_entry_component(component, parent_node, indent)
            return
        attributes = self.attributesDefault
        if type(component) in self.attributesMap:
            attributes = self.attributesMap[type(component)]

        if parent_node is None:
            element = Element(component.name)
        else:
            element = SubElement(parent_node, component.name)

        if IComponent.offsetTag in attributes:
            element.attrib[component.offsetTag] = hex(component.offset)
        if IComponent.sizeTag in attributes:
            element.attrib[component.sizeTag] = hex(component.size)

        if component.encryption_key_component:
            if IComponent.valueTag in attributes:
                element.attrib[component.valueTag] = '(encrypted)'
        elif component.children and (self.maxLevel is None or indent < self.maxLevel):
            for child in component.children:
                if child._is_enabled() and (not self.skipEmpty or child.size > 0):
                    self._create_xml_entry(child, element, indent + 1)
        elif IComponent.valueTag in attributes:
            element.attrib[component.valueTag] = self._format_value(component)
        return element

    def _create_xml_entry_table_entry_component(self, component: TableEntryComponent, parent_node, indent):
        element = SubElement(parent_node, component.name)
        if component.entry is not None:
            return self._create_xml_entry(component.entry,
                                          element,
                                          indent)
        return element

    def _format_value(self, component):
        if component.size and component.size > self.maxValueSize:
            return '({} bytes)'.format(component.size)
        else:
            if type(component.value) is str:
                return prepare_string_to_xml(component.get_value_string())
            else:
                return component.get_value_string()


class XmlInfoFormatter(XmlMapFormatter):
    attributesDefault = [IComponent.offsetTag, IComponent.sizeTag, IComponent.valueTag]
    maxLevel = None
    skipEmpty = False


class MapGenerator:

    def __init__(self, formatter_class: type):
        self.formatter = formatter_class

    def generate_map(self, map_root: IComponent, map_path, ext=''):
        formatter_inst = self.formatter()
        target_ext = self.formatter.mapExt
        if ext:
            target_ext = ext
        final_path = map_path + target_ext
        with open(final_path, 'w') as file:
            file.write(formatter_inst.create_map(map_root))
        return final_path
