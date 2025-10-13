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
from abc import ABC
from enum import Enum
from typing import Optional, Dict, Callable, Union

from .Converter import Converter
from .LibException import ValidateException, ComponentAttributeException
from .utils import parse_json_str


class AttributeGroup(ABC):
    """Base class for attribute groups. Should be used as abstract class by inheriting from it and defining params."""
    # { name: convert function }
    property_definitions: Dict[str, Callable] = {}

    def __init__(self, formula: Optional[str]):
        """
        :param formula: Json string with dictionary of prams {'param_name': 'value'}.
        """
        self._set_default_attributes()
        params_dict = parse_json_str(formula) if formula else {}

        for key, raw_value in params_dict.items():
            if key not in self.property_definitions:
                raise ComponentAttributeException(f"Unknown attribute: '{key}'.")
            val = self.property_definitions[key](raw_value)
            setattr(self, key, val)

    def _set_default_attributes(self):
        pass


class UiParams(AttributeGroup):
    """Holds values and handles operations on ui_params properties of IComponent"""
    xml_tag = 'ui_params'
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_LABEL_LENGTH = 256

    class Tags:
        LABEL = 'label'
        READ_ONLY = 'read_only'
        VISIBLE = 'visible'
        OPTION_TYPE = 'option_type'
        DESCRIPTION = 'description'
        REGION_OPTION = 'region_option'
        REGION_VERSION = 'region_version'
        QUICK_OPTION = 'quick_option'
        EXPANDABLE = 'expandable'
        ORDER_PRIORITY = 'order_priority'
        SETTINGS_ORDER = 'settings_order'

    def __init__(self, formula: Optional[str], component=None):
        self.component: Optional['IComponent'] = component
        super().__init__(formula)

    def _set_default_attributes(self):
        self.label: str = self.component.name if self.component else None
        self.read_only: bool = False
        self.visible: bool = True
        self.option_type: Optional[str] = None
        self.description: Optional[str] = None
        self.region_option: Optional[str] = None
        self.settings_order: Optional[str] = None
        self.region_version: bool = False
        self.quick_option: bool = False
        self.expandable: bool = False
        self.order_priority: Optional[int] = None

    @classmethod
    def is_ui_param(cls, param: str):
        return param in UiParams.property_definitions

    def validate(self):
        component_name = self.component.name if self.component else ''
        self._validate_description_lenght(component_name)
        self._validate_label_length(component_name)

    def _validate_description_lenght(self, comp_name):
        if self.description and len(self.description) > UiParams.MAX_DESCRIPTION_LENGTH:
            raise ValidateException("Description too long", self.description, component_name=comp_name)

    def _validate_label_length(self, comp_name):
        if self.label and len(self.label) > UiParams.MAX_LABEL_LENGTH:
            raise ValidateException("Label too long", self.label, component_name=comp_name)


UiParams.property_definitions = {
    UiParams.Tags.READ_ONLY: Converter.string_to_bool,
    UiParams.Tags.VISIBLE: Converter.string_to_bool,
    UiParams.Tags.OPTION_TYPE: Converter.no_conversion,
    UiParams.Tags.DESCRIPTION: Converter.no_conversion,
    UiParams.Tags.LABEL: Converter.no_conversion,
    UiParams.Tags.REGION_OPTION: Converter.no_conversion,
    UiParams.Tags.REGION_VERSION: Converter.string_to_bool,
    UiParams.Tags.QUICK_OPTION: Converter.string_to_bool,
    UiParams.Tags.EXPANDABLE: Converter.string_to_bool,
}


class IterableUiParams(UiParams):
    """
        Special case of ui_params for iterables. Iterable components are also defined with an additional attribute:
         order_priority to be added to property_definitions.
    """
    def __init__(self, formula: Optional[str], component=None):
        self.property_definitions = self.property_definitions.copy()
        self.property_definitions.update({UiParams.Tags.ORDER_PRIORITY: Converter.string_to_int})
        super().__init__(formula, component)


class GroupUiParams(UiParams):
    """
    Special case of ui_params for groups. Contains handling of visible property. For it to work properly, we need to
    call `set_component` to pass reference to parent component. Group components are defined with an additional
     attributes such as settings_order and order_priority.
    """

    def __init__(self, formula: Optional[str], component=None):
        self._visible: bool = True
        self.property_definitions = self.property_definitions.copy()
        self.property_definitions.update({UiParams.Tags.SETTINGS_ORDER: Converter.no_conversion,
                                          UiParams.Tags.ORDER_PRIORITY: Converter.string_to_int})
        super().__init__(formula, component)

    @property
    def visible(self) -> bool:
        return self._visible and self.component and any(child.ui_params.visible for child in self.component.children)

    @visible.setter
    def visible(self, value: bool):
        self._visible = value

    def validate(self):
        super().validate()
        self._validate_setting_order_value()

    def _validate_setting_order_value(self):
        component_name = self.component.name if self.component else ''
        allowed_values = ['By order', 'By feature']
        if self.settings_order is not None and self.settings_order not in allowed_values:
            raise ValidateException(f'Allowed values of \'{UiParams.Tags.SETTINGS_ORDER}\' are: {allowed_values}',
                                    self.settings_order,
                                    component_name=component_name)


class ReadOnlyUiParams(UiParams):
    def _set_default_attributes(self):
        super()._set_default_attributes()
        self.read_only = True


class DecompositionAttributes(AttributeGroup):
    # pylint: disable=unnecessary-lambda
    property_definitions: Dict[str, Callable] = {
        'skip': Converter.no_conversion,
        'enabled': Converter.no_conversion,
        'identifier': lambda s: DecompositionAttributes.Identifier(s),
        'link': lambda s: DecompositionAttributes.Link(s),
        'validate': Converter.string_to_bool
    }
    # pylint: enable=unnecessary-lambda

    class Link:
        def __init__(self, link: Union[str, dict]):
            if isinstance(link, str):
                self.destination = link
                self.value = None
            else:
                self.destination = link.get('destination', None)
                self.value = link.get('value', None)
                if not self.destination:
                    raise ComponentAttributeException("'link' attribute needs to have 'destination' specified.")

    class Identifier:
        class IdentifierType(Enum):
            NODE = 'node'
            FORMULA = 'formula'

        def __init__(self, identifier: Union[Dict, str]):
            if isinstance(identifier, str):
                self.identifier_type = self.IdentifierType.NODE
                self.formula: str = identifier
            else:
                self.identifier_type = self.IdentifierType(identifier.get('type', self.IdentifierType.NODE.value))
                self.formula = identifier.get('formula')

    def _set_default_attributes(self):
        self.skip: Optional[str] = None
        self.enabled: Optional[str] = None
        self.identifier: Optional[DecompositionAttributes.Identifier] = None
        self.link: Optional[DecompositionAttributes.Link] = None
        self.validate: bool = True
