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
from datetime import date, datetime
from enum import Enum

from ..exceptions import GeneralException
from .IComponent import IComponent


class DateComponent(IComponent):

    date_format: str = '%Y-%m-%d'
    date_format_human_readable: str = 'YYYY-MM-DD'

    class ComponentProperty(Enum):
        Bcd = "bcd"

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self._set_value(date.today())
        self.read_only = True

    def _parse_string_value(self, value):
        try:
            date_obj: date = datetime.strptime(value, self.date_format).date()
            return date_obj
        except ValueError:
            raise GeneralException(f"{value} does not match {self.date_format_human_readable}")

    def _get_property(self, component_property, _=False):
        if component_property == self.ComponentProperty.Bcd:
            int_date = int(str(self.value.year).zfill(4) + str(self.value.month).zfill(2)
                           + str(self.value.day).zfill(2), 16)
            return int_date.to_bytes(4, self.littleOrder)

    def get_value_string(self):
        return self.value.isoformat()
