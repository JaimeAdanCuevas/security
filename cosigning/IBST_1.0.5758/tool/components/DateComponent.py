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
from datetime import date, datetime
from enum import Enum

from ..AttributeGroup import ReadOnlyUiParams
from .IComponent import IComponent
from ..LibException import ComponentException


class DateComponent(IComponent):
    """Represents a date in YYYY-MM-DD format, gets the current date if the value is not provided.

    Date component special properties

    Special property    Description
    ----------------    -----------
    bcd                 Gets the date in BCD format
    """

    date_format: str = '%Y-%m-%d'
    date_format_human_readable: str = 'YYYY-MM-DD'

    class ComponentProperty(Enum):
        BCD = "bcd"

    ui_params_class = ReadOnlyUiParams

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        if self.value is None:
            self.set_value(date.today())

    def get_parsed_string_value(self, value):
        try:
            date_obj: date = datetime.strptime(value, self.date_format).date()
            return date_obj
        except ValueError as e:
            raise ComponentException(f"{value} does not match {self.date_format_human_readable}") from e

    def _get_property(self, component_property, _=False, __=False):
        if component_property == self.ComponentProperty.BCD:
            int_date = int(str(self.value.year).zfill(4) + str(self.value.month).zfill(2)
                           + str(self.value.day).zfill(2), 16)
            return int_date.to_bytes(4, self.littleOrder)
        return None

    def get_val_string(self, val):
        return None if val is None else val.isoformat()
