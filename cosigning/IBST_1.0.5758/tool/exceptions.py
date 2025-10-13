#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2022 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
from .ColorPrint import ColorPrint


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


class DependencyException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class WrongFileException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class MissingFileException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class FileAccessException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class XmlSecurityException(GeneralException):
    def __init__(self, message, component_name='', class_ref=None):
        super().__init__(message, component_name, class_ref)


class ExternalProcessException(GeneralException):
    def __init__(self, message, executable, arguments=None, cwd=None, output=None, error_output=None):
        super().__init__(message)
        self.executable = executable
        self.arguments = arguments
        self.cwd = cwd
        self.output = output
        self.error_output = error_output

    def __str__(self):
        args = ''
        if self.arguments:
            if isinstance(self.arguments, str):
                args = ' ' + self.arguments
            else:
                args = ' ' + ' '.join(self.arguments)
        name = f'\nCommand: {self.executable}{args}' if self.executable else ''
        cwd = f'\nIn: {self.cwd}' if self.cwd else ''
        error_message = f'\nError: {self.error_output}' if self.error_output else ''
        output_message = f'\nOutput: {self.output}' if self.output else ''
        ColorPrint.debug(f'{self.message}{name}{cwd}{output_message}{error_message}')
        return f'{self.message}'


class DecompositionException(GeneralException):  # pragma: no cover: Class usage moved to plugin code
    def __init__(self, message, container=None, element=None):
        super().__init__(message)
        self.container = container
        self.element = element


class PathTooLongException(GeneralException):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return self.message


class SnapshotException(GeneralException):
    """
    Exception raised during processing configuration snapshots.
    """
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return self.message


class CustomActionException(GeneralException):
    """
    Exception raised during registering or processing custom actions.
    """
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return self.message
