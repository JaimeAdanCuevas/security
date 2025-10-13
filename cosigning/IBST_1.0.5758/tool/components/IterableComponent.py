#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2020-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
import re
import string
from copy import copy
from enum import Enum
from typing import Optional, Dict, Set, List

from lxml.etree import SubElement, Comment, Element  # nosec

from .IComponent import IComponent
from .IComponentParams import ComponentParams
from ..AttributeGroup import UiParams, IterableUiParams
from ..Converter import Converter
from ..dependencies.Dependency import Dependency
from ..LibException import ComponentException, ComponentAttributeException, ValidateException
from ..structures import Buffer


class IterableComponent(IComponent):
    # pylint: disable=line-too-long
    """A special component used to group settings so the user can provide chosen amount of such groups.
    They can be then referenced by index or in a table component in layout or decomposition sections.
    The maximum amount of entries can be limited by max_entry_count attribute.
    The user can define his own entries through the override file. Example of an iterable:

    ```xml
    <iterable name="images" max_entry_count="8">
      <entry>
        <file name="image" value="path/to/file1.bin" />
        <string name="type" value="type1" />
        <number name="id" value="1" />
      </entry>
      <entry>
        <file name="image" value="path/to/file2.bin" />
        <string name="type" value="type2" />
        <number name="id" value="5" />
      </entry>
      <default>
        <file name="image" value="" />
        <string name="type" value="default" />
        <number name="id" value="0" />
      </default>
    </iterable>
    ```

    Note - default entry is required to define the proper entry structure, but cannot be referenced.

    Iterable component special properties

    Special property    Description
    ----------------    -----------
    size                Gets the amount of entries (not including the default)
    path                Gets an array of indexes, used rather only for table count (more on that later)
    max_size            Gets the max_entry_count attribute value
    data                Gets entire data of the iterable, can only be used if all the non-file components (like number, string) have the *size* attribute defined
    """
    # pylint: enable=line-too-long

    uniqueNamePattern = '(?:.(?!-))+$'
    user_comment = '''It is recommended that the user modifies the iterables using the Modular Flash Image Tool's
    Graphical User Interface to avoid misconfiguration.'''

    ui_params_class = IterableUiParams

    class ComponentProperty(Enum):
        SIZE = "size"
        DATA = "data"
        INDICES = "indices"
        MAX_SIZE = 'max_entry_count'
        VALUES_ARRAY = "values_array"

    class Tags(IComponent.Tags):
        ITERABLE = 'iterable'
        MAX_ENTRIES = 'max_entry_count'

    def __init__(self, xml_node, **kwargs):
        self.default_element: Optional[IComponent] = None
        self.default_entries_list = []
        self._data = None
        self.max_size = None
        self.children_by_index = {}
        self.descendants_by_unique_id = {}
        self.starting_indices: Set[int] = set()
        self.starting_entries: Dict[int: IComponent] = {}
        self.starting_labels: Dict[int: str] = {}
        super().__init__(xml_node, **kwargs)

    def _parse_additional_attributes(self, xml_node):
        max_size_formula = self._parse_attribute(xml_node, self.Tags.MAX_ENTRIES, False, None)
        if max_size_formula is not None:
            self.max_size = self.calculate_value(max_size_formula)

    def build_layout(self, buffer, clear_build_settings: bool = False):
        raise ComponentException('Trying to build GUI only element', self.name)

    def build(self, buffer):
        raise ComponentException('Trying to build GUI only element', self.name)

    @property
    def indices(self):
        return sorted(self.children_by_index.keys())

    @property
    def data(self):
        self._load_data()
        return self._data

    @property
    def entries_count(self):
        return len(self.children)

    def validate_child_value(self, child: IComponent, value):
        self._validate_id_setting(child, value)
        self._update_iterable(child, value)

    def _validate_id_setting(self, child: IComponent, value: int):
        """
        Checks whether new value is unique if the current setting is a child of iterable with id_setting defined.
        """
        if self.params and self.params.is_id_setting_set():
            id_setting_name = self.params.value_str(ComponentParams.ParamsAttr.ID_SETTING)
            if not self.params.is_id_counter_start_set():
                raise ComponentAttributeException(
                    f"Missing attribute '{ComponentParams.ParamsAttr.ID_COUNTER_START.value}'. "
                    f"Please check component configuration for '{self.name}'.")
            id_counter_start_value = self.params.value_int(ComponentParams.ParamsAttr.ID_COUNTER_START)
            setting_name = re.search('(?:.(?!-))+$', child.name).group(0).strip('-')

            if setting_name == id_setting_name:
                if value < id_counter_start_value:
                    # id_counter_start should have higher priority then value_min
                    raise ComponentAttributeException(f"Value '{child.display_func(value)}' of setting "
                                                      f"'{child.name}' must be greater then or equal to "
                                                      f"{ComponentParams.ParamsAttr.ID_COUNTER_START.value} "
                                                      f"(value={hex(id_counter_start_value)}).")
                if value in self.descendants_by_unique_id and \
                   self.descendants_by_unique_id[value].name != child.name:
                    # it must stop any procedure (ie. build) as we don't want to create confusion
                    # using ValidationException will finish with the warning which can be omitted by the user
                    raise ComponentAttributeException(
                        f"Value '{child.display_func(value)}' of setting '{child.name}' must be unique, " +
                        "but its already used in setting " +
                        f"'{self.descendants_by_unique_id[value].name}'.")

    def _update_iterable(self, child: IComponent, value: int):
        """
        Updates collection of iterable descendants with unique id setting,
        if the current setting is a child of iterable with id_setting defined.
        """
        if self.params and self.params.is_id_setting_set():
            id_setting_name = self.params.value_str(ComponentParams.ParamsAttr.ID_SETTING)
            setting_name = re.search(IterableComponent.uniqueNamePattern, child.name).group(0).strip('-')
            if id_setting_name and setting_name == id_setting_name:
                if child.value in self.descendants_by_unique_id:
                    del self.descendants_by_unique_id[child.value]
                self.descendants_by_unique_id[value] = child

    def _load_data(self):
        buffer = Buffer(-1, 100000)
        for entry in self.children:
            entry.build_layout(buffer)
        buffer.flush()
        for entry in self.children:
            entry.build(buffer)
        self._data = buffer[0:buffer.tell()]
        buffer.flush()

    def _get_property(self, component_property, _=False, __=False):
        if component_property == self.ComponentProperty.DATA:
            return self.data
        if component_property == self.ComponentProperty.SIZE:
            return self.entries_count
        if component_property == self.ComponentProperty.INDICES:
            return self.indices
        if component_property == self.ComponentProperty.MAX_SIZE:
            return self.max_size
        if component_property == self.ComponentProperty.VALUES_ARRAY:
            return [[ch.value for ch in child.children] for child in self.children]
        return None

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst.children = self.children
        dst.children_by_name = self.children_by_name

    def _set_indexless_children(self, children: List[Element], default_entry_node):
        """After adding all children with index specified, remaining entries should fill unused indexes."""
        index = 0
        for child_node in children:
            index = self._get_free_index(index)
            child_node.attrib[self.Tags.INDEX] = str(index)
            self._parse_entry_node(child_node, default_entry_node)
            index += 1

    def _set_starting_values(self):
        """
        Saves list of indices, children and default labels.
        Should only be called once children from plugin are parsed and haven't been edited by user.
        """
        self.starting_indices = set(self.children_by_index.keys())
        self.starting_entries = copy(self.children_by_name)
        self.starting_labels = {i: v.display_name for i, v in self.children_by_index.items()}

    def _parse_children(self, xml_node, **kwargs):
        self.children = []
        self.children_by_name = {}
        if self.dependency_formula and Dependency.Tags.GET in self.dependency_formula:
            return
        try:
            self._parse_default_node(xml_node)

            indexless_children: List[Element] = []
            default_entry_node = next(node for node in xml_node if node.tag == IterableEntryComponent.Tags.DEFAULT)
            for child_node in xml_node:
                if child_node.tag is Comment:
                    continue
                if child_node.tag == IterableEntryComponent.Tags.DEFAULT:
                    continue
                if child_node.tag == IterableEntryComponent.Tags.ENTRY:
                    if self.Tags.INDEX in child_node.attrib:
                        self._parse_entry_node(child_node, default_entry_node)
                    else:
                        indexless_children.append(child_node)
                else:
                    raise ComponentException(
                        f'Iterable children must be either "{IterableEntryComponent.Tags.ENTRY}" '
                        f'or "{IterableEntryComponent.Tags.DEFAULT}" - {child_node.tag} provided')
            self._set_indexless_children(indexless_children, default_entry_node)
            self._set_starting_values()

            if self._skip_calculates:
                # We clear children after parsing them, to keep starting indices and entries
                self._clear_children()
        except ComponentException as ex:
            self.trace_exception(ex)

    def _clear_children(self):
        self.children.clear()
        self.children_by_name.clear()
        self.children_by_index.clear()

    def _get_free_index(self, start: int = 0):
        """Gets lowest free index equal or greater than 'start'."""
        while not self.max_size or start < self.max_size:
            if start not in self.children_by_index:
                return start
            start += 1
        raise ComponentException('Number of entries exceeds max_size')

    def _get_free_setting_id(self, component: IComponent, start: int):
        """Gets lowest free setting id equal or greater than 'start'."""
        value_max = component.params.value_int(ComponentParams.ParamsAttr.VALUE_MAX)
        while not value_max or start <= value_max:
            if start not in self.descendants_by_unique_id:
                return start
            start += 1
        raise ComponentException(f'Number of ids exceeds value_max: {value_max}.')

    def _parse_default_node(self, xml_node):
        defaults = xml_node.findall(IterableEntryComponent.Tags.DEFAULT)
        if len(defaults) == 0:
            raise ComponentException(f'No default definition for {self.name} iterable', self.name)
        if len(defaults) > 1:
            raise ComponentException(f'There is more than one default definition for {self.name} iterable', self.name)
        default_node = defaults[0]
        self._fill_default_structure(default_node)
        self.default_element = self.componentFactory.create_component(default_node,
                                                                      skip_calculates=self._skip_calculates)
        self.default_element.initialize_defaults()

    def _parse_entry_node(self, child_node, default_entry_node):
        index = child_node.attrib[self.Tags.INDEX]
        if index.isdigit():
            index = Converter.string_to_int(index)
            if index in self.children_by_index:
                raise ComponentException(f'Index with value {index} already used')
        else:
            raise ComponentException('Iterable entry index must be numeric value')
        if self.max_size and index >= self.max_size:
            raise ComponentException(f'Number of entries exceeds max_size {self.max_size}')
        if self.Tags.NAME not in child_node.attrib:
            child_node.attrib[self.Tags.NAME] = IterableEntryComponent.Tags.ENTRY
        self._validate_entry_structure(child_node, index)
        self.copy_attributes_from_default_node(child_node, default_entry_node)
        component = self.componentFactory.create_component(child_node, parent=self, index=index,
                                                           skip_calculates=self._skip_calculates,
                                                           iterable_descendant=True)
        self.children_by_index[index] = component

    def copy_attributes_from_default_node(self, entry_node, default_entry_node):
        for entry_element in entry_node:
            if entry_element.attrib:
                default_entry_element = next((default_element for default_element in default_entry_node
                                             if default_element.attrib[self.Tags.NAME]
                                              == entry_element.attrib[self.Tags.NAME]), None)
                for attribute, value in default_entry_element.items():
                    if attribute not in entry_element.attrib:
                        entry_element.set(attribute, value)
                self.copy_attributes_from_default_node(entry_element, default_entry_element)

    def _get_child(self, child_name):
        if self.children_by_name is None:
            raise ComponentException(f"'{self.name}' has no children", self.name)
        if child_name in self.children_by_name:
            return self.children_by_name[child_name]
        child_name_regex = re.search(rf'^{self.name}\[(\d+)\]$', child_name)
        index = int(child_name_regex.group(1)) if child_name_regex else None
        if index is not None and self.max_size is not None and index >= self.max_size:
            raise ComponentException(
                f'Trying to get configuration for non-existing index. Exceeded max_size: {index}', self.name)
        if index is not None and hasattr(self, 'starting_entries') and child_name in self.starting_entries:
            child = self._add_entry_from_default(index)
            self._update_entry_from_starting_entries(child, child_name)
            return child
        if index is not None and self.default_element:
            return self._add_entry_from_default(index)
        raise ComponentException(
            f"No '{child_name}' child. Choose one of: {', '.join(self.children_by_name.keys())}", self.name)

    def _update_entry_from_starting_entries(self, entry, entry_name):
        starting_entry = self.starting_entries[entry_name]
        for c in entry.children:
            c.value = starting_entry.children_by_name[c.name].value
            c.default_value = starting_entry.children_by_name[c.name].default_value

    def to_xml_node(self, parent, simple_xml: bool, save_user_notes=True):
        if not self.is_setting_saveable:
            return

        self._append_user_comment(parent, simple_xml)

        for index in sorted(self.starting_indices.union(self.children_by_index.keys())):
            entry = self.children_by_index.get(index, None)
            if entry is None:
                SubElement(parent, 'setting', {self.Tags.NAME: f'{self.name}[{index}]:remove', self.Tags.VALUE: 'true'})
            else:
                entry_replaced = entry.from_default and index in self.starting_indices
                if entry_replaced:
                    SubElement(parent, 'setting', {self.Tags.NAME: f'{entry.name}:replace', self.Tags.VALUE: 'true'})
                entry_added = entry.from_default and index not in self.starting_indices
                setting_children = [child for child in entry.descendants if child.node_tag != self.Tags.GROUP]
                save_full_iterable = self._check_children_have_non_defaults(setting_children) or entry_replaced \
                                     or entry_added or entry.display_name != self.starting_labels[index]
                if not simple_xml or save_full_iterable:
                    SubElement(parent, 'setting', {self.Tags.NAME: f'{entry.name}:label',
                                                   self.Tags.VALUE: entry.display_name})
                if save_full_iterable or not simple_xml:
                    for child in setting_children:
                        child.to_xml_node(parent, simple_xml)

    def _append_user_comment(self, parent_node, simple_xml):
        comment = Comment(self.user_comment)

        if not simple_xml and len(self.starting_indices.union(self.children_by_index.keys())) > 0:
            parent_node.append(comment)
            return

        for index in sorted(self.starting_indices.union(self.children_by_index.keys())):
            entry = self.children_by_index.get(index, None)

            if entry is None:
                parent_node.append(comment)
                return

            entry_replaced = entry.from_default and index in self.starting_indices
            entry_added = entry.from_default and index not in self.starting_indices
            setting_children = [child for child in entry.descendants if child.node_tag != self.Tags.GROUP]

            if self._check_children_have_non_defaults(setting_children) or entry_replaced or entry_added:
                parent_node.append(comment)
                return

    @staticmethod
    def _check_children_have_non_defaults(children):
        return any(child.has_non_default_value or child.has_annotations for child in children)

    def _fill_default_structure(self, default_node):
        self.default_entries_list = []
        for node in default_node.iter():
            if node.tag == self.Tags.GROUP or node.tag == IterableEntryComponent.Tags.DEFAULT:
                continue
            setting_name = self.get_name(node)
            # names generated can have additional number at the end which can vary between entries
            setting_name = setting_name.rstrip(string.digits)
            self.default_entries_list.append(setting_name)

    def _validate_entry_structure(self, entry_node, index):
        node_settings = [self.get_name(setting).rstrip(string.digits) for setting in entry_node.iter()
                         if setting.tag != self.Tags.GROUP and setting.tag != IterableEntryComponent.Tags.ENTRY]
        if len(node_settings) != len(self.default_entries_list):
            raise ComponentException(f"Number of settings in {index} entry doesn't match number of default entries'",
                                     self.name)
        for mandatory_default_name in self.default_entries_list:
            if mandatory_default_name not in node_settings:
                raise ComponentException(f"Mandatory setting name: {mandatory_default_name} missing in"
                                         f" {index} entry of {self.name} iterable")

    def make_component_iterable_descendant(self, component: IComponent, index: int):
        component.iterable_descendant = True
        component.iterable_root = self
        if not component.parent:
            component.parent = self
        component.iterable_index = index
        component.original_name = component.name
        if component.parent == self:
            component.name = f'{self.name}[{index}]'
        else:
            component.name = f'{self.name}[{index}].{component.original_name}'
        if hasattr(component, IComponent.Tags.CHILDREN):
            for child in component.children:
                self._update_iterable_entry_for_gui(component, child)
                self.make_component_iterable_descendant(child, index)

    def _update_iterable_entry_for_gui(self, component: IComponent, child: IComponent):
        if component.iterable_root.params and component.iterable_root.params.is_id_setting_set():
            if not component.iterable_root.params.is_id_counter_start_set():
                raise ComponentAttributeException(
                    f"Missing attribute '{ComponentParams.ParamsAttr.ID_COUNTER_START.value}'. "
                    f"Please check component configuration for '{component.iterable_root.name}'.")
            id_setting_name = component.iterable_root.params.value_str(ComponentParams.ParamsAttr.ID_SETTING)
            unique_child_id_match = re.search(IterableComponent.uniqueNamePattern, child.name)
            unique_setting_name = unique_child_id_match.group(0).strip('-')
            if id_setting_name is not None and unique_setting_name == id_setting_name:
                id_counter_start = component.iterable_root.params.value_int(ComponentParams.ParamsAttr.ID_COUNTER_START)
                child.value = self._get_free_setting_id(child, id_counter_start)
                component.id_setting_value = str(hex(child.value))
                component.id_setting_name = child.name
                self.descendants_by_unique_id[child.value] = child

    def _add_entry_from_default(self, index: int):
        entry = self.default_element.semideepcopy()
        entry.name = f'{IterableEntryComponent.Tags.ENTRY}{index}'
        entry.entry_label = str(self.display_name)
        entry.node_tag = IterableEntryComponent.Tags.ENTRY
        entry.index = index
        if entry.map_name is None:
            entry.map_name = f'{IterableEntryComponent.Tags.ENTRY}[{index}]'
        self.make_component_iterable_descendant(entry, index)
        self._add_entry(entry, index)
        return entry

    def _add_entry(self, entry, index: int):
        self.children.append(entry)
        self.children_by_name[entry.name] = entry
        self.children_by_index[index] = entry

    def add_new_entry(self):
        index = self._get_free_index()
        return self._add_entry_from_default(index)

    def remove_entry(self, index: int):
        try:
            element = self.children_by_index[index]
            self.remove_child(element.name)
            del self.children_by_index[index]
            if element.children:
                for item in element.children:
                    if getattr(self, 'descendants_by_unique_id', None) and item.value in self.descendants_by_unique_id \
                            and self.descendants_by_unique_id[item.value].name == item.name:
                        del self.descendants_by_unique_id[item.value]
        except KeyError as e:
            raise ComponentException("Trying to remove non existing element") from e

    @property
    def has_non_default_value(self):
        if len(self.starting_entries) - len(self.children) != 0:
            return True
        if any(entry.from_default for entry in self.children):
            return True
        if any(c.display_name != self.starting_labels[i] for i, c in self.children_by_index.items()):
            return True
        for entry in self.children:
            if any(entry_setting.has_non_default_value for entry_setting in entry.children):
                return True
        return False

    @property
    def has_annotations(self):
        for entry in self.children:
            if any(entry_setting.has_annotations for entry_setting in entry.children):
                return True

        return False

    def clear_children(self):
        self.children_by_index.clear()
        self.children_by_name.clear()
        self.children.clear()

    @staticmethod
    def flat_tree(component):
        iterable_flat = IterableComponent._get_flat_struct(component)
        for entry in iterable_flat:
            yield entry

    @staticmethod
    def _get_flat_struct(component):
        iterable_flat = []
        for entry in component.children:
            if entry.children:
                iterable_flat.extend(IterableComponent._get_flat_struct(entry))
            else:
                iterable_flat.append(entry)

        return iterable_flat

    def copy_values_from_entry(self, source_entry, target_entry, entry_name):
        """Recursively copies values from source_entry children to target_entry children."""
        for source_child in source_entry.children:
            target_child = target_entry.children_by_name[f"{entry_name}.{source_child.name}"]
            target_child.value = source_child.value
            target_child.default_value = source_child.default_value
            self.copy_values_from_entry(source_child, target_child, entry_name)
        if isinstance(target_entry, IterableEntryComponent) and isinstance(source_entry, IterableEntryComponent):
            target_entry.from_default = source_entry.from_default


class IterableEntryComponent(IComponent):
    iterable_index = None
    from_default = None

    class Tags(IComponent.Tags):
        DEFAULT = 'default'
        ENTRY = 'entry'
        ENTRY_LABEL = 'entry_label'

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.from_default = xml_node.tag == IterableEntryComponent.Tags.DEFAULT

    @property
    def entry_label(self) -> Optional[str]:
        return self._entry_label

    @entry_label.setter
    def entry_label(self, value: Optional[str]):
        if value is not None:
            self._validate_entry_label(value)
        self._entry_label = value

    def _validate_entry_label(self, entry_label: str):
        if entry_label and len(entry_label) > UiParams.MAX_LABEL_LENGTH:
            raise ValidateException("Iterable entry label too long", entry_label, component_name=self.name)

    @property
    def display_name(self) -> str:
        return self.entry_label if self.entry_label else super().display_name

    def _parse_additional_attributes(self, xml_node):
        self.entry_label = self._parse_attribute(xml_node, self.Tags.ENTRY_LABEL, False, None)

    def _init_iterable_desc_properties(self, kwargs, component):
        if kwargs.get(component.Tags.ITERABLE_DESCENDANT, False) or component.parent and \
                component.parent.iterable_descendant:
            if not component.parent:
                raise ComponentException('Component set as Iterable Descendant must have parent')
            iterable_root = component.parent.iterable_root if component.parent.iterable_root else component.parent
            index = component.parent.iterable_index if component.parent.iterable_descendant else component.index
            iterable_root.make_component_iterable_descendant(component, index)
