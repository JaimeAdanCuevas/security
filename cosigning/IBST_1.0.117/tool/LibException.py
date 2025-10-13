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
from .LibConfig import LibConfig


class LibException(Exception):
    pass


class ComponentException(LibException):

    trace = []

    def __init__(self, message, object_name=""):
        super().__init__(message, object_name)
        self.trace = []
        self.trace.append(object_name)

    def __str__(self):
        return self.args[0] + "\nIn: " + LibConfig.pathSeparator.join(reversed(self.trace))


class FunctionException(LibException):
    pass


class ValueException(ComponentException):
    def __init__(self, message, value, component_name=''):
        super().__init__("Cannot set value: " + str(value) + "\n" + message, component_name)
        self.message = str(self)


class DependencyException(LibException):
    owner_setting_path = None

    def __init__(self, message, dependency=None, owner_component=None):
        super().__init__(message)
        if dependency and dependency.owner_setting_ref:
            self.owner_setting_path = dependency.owner_setting_ref.get_string_path()
        elif owner_component:
            self.owner_setting_path = owner_component.get_string_path()
        else:
            self.owner_setting_path = '<not specified>'

    def __str__(self):
        return self.args[0] + "\nIn: " + self.owner_setting_path

