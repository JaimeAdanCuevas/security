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


class GeneralException(Exception):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message)
        self.class_ref = class_ref
        self.component_name = component_name
        self.message = message

    def __str__(self):
        if self.component_name:
            name = self.component_name
        elif self.class_ref:
            name = self.class_ref.__name__
        else:
            return self.message
        return f'{self.message}\nComponent name: {name}'


class MissingAttributeException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class InvalidAttributeException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class InvalidSizeException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class JSONException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class WrongTypeException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class ActionException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class DependencyException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)
