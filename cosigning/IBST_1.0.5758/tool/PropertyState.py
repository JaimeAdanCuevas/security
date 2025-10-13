"""
INTEL CONFIDENTIAL
Copyright 2021-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
import copy
from enum import Enum
from typing import List, Tuple, Set

from .LibException import SnapshotException


class PropertyState:
    """
    Class that describes component's property state. Used for configuration snapshots.
    """

    class SupportedProperties(Enum):
        """
        Enum that helps avoiding hard coding property names for the cases where we expect to use it explicitly.
        """

        VALUE = "value"
        USER_SET_VALUE = "user_set_value"
        ENABLED = "enabled"
        ENABLED_FORMULA = "enabled_formula"
        EXISTS = "_exists"
        XML_SAVE = "_xml_save"
        XML_SAVE_FORMULA = "xml_save_formula"
        NON_EXIST_HELP_TEXT = "non_exist_help_text"
        SRC_EXISTS_SETTING = "src_exists_setting"
        VISIBLE = "visible"
        PARAMS = "params"

    def __init__(self, property_name, value):
        if not isinstance(property_name, PropertyState.SupportedProperties) and not isinstance(property_name, str):
            raise SnapshotException("PropertyState accepts only instance of "
                                    "SupportedProperties enum or string as property_name")

        self._property_name = property_name.value if isinstance(property_name,
                                                                PropertyState.SupportedProperties) else property_name
        if isinstance(value, List):
            self.value = copy.copy(value)
        else:
            self.value = value

    def __hash__(self):
        return hash(self._property_name)

    def __eq__(self, other):
        if not isinstance(other, PropertyState):
            return False

        return self._property_name == other.property_name

    @property
    def property_name(self):
        """
        Getter for property_name
        :return: Object's property_name.
        """
        return self._property_name


ComponentPreChangeState = Tuple['IComponent', Set[PropertyState]]
