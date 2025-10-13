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
from typing import Iterable

from .LibConfig import LibConfig


class LibException(Exception):
    def __init__(self, message: str, *args):
        """Base for all exceptions used in library."""
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return self.message


class XmlAttrException(LibException):
    pass


class ComponentException(LibException):
    trace = []

    def __init__(self, message, object_name=""):
        super().__init__(message, object_name)
        self.trace = []
        self.trace.append(object_name)
        self._object_name = object_name

    def __str__(self):
        message = self.args[0]
        if any(self.trace):
            message += "\nIn: " + LibConfig.pathSeparator.join(reversed(self.trace))
        return message

    @property
    def object_name(self):
        return self._object_name

    @object_name.setter
    def object_name(self, value):
        if self._object_name in self.trace:
            self.trace.remove(self._object_name)
        self._object_name = value
        self.trace.insert(0, value)


def trim_user_input(value):
    max_value_length_to_display = 300  # arbitrary value based on 64 bytes for hashes (128) and MAX_PATH (260)
    value_str = str(value)
    if len(value_str) > max_value_length_to_display:
        return value_str[:max_value_length_to_display] + "..."
    return value


class ValueException(ComponentException):
    def __init__(self, message, value, component_name=''):
        value_str = trim_user_input(value)
        super().__init__(f"Cannot set value: {value_str}\n{message}", component_name)
        self.message = str(self)


class ValidateException(ValueException):
    def __init__(self, message, value, min_max='', value_list='', component_name=''):
        if value_list:
            message += f"\nPossible values: {value_list}"
        super().__init__(message, value, component_name)
        self.message = str(self)
        self.min_max = min_max
        self.value_list = value_list
        self.value = value


class ComponentAttributeException(ComponentException):
    pass


class WrongDecompositionFileException(ComponentException):
    exc_message = 'Incorrect file {path} in {path_split}.'

    def __init__(self, path: str, path_split: str, object_name: str):
        super().__init__(self.exc_message.format(path=path, path_split=path_split), object_name)


class DecompositionFileNotGiven(ComponentException):
    exc_message = 'File for decomposition was not set in {path_split}.'

    def __init__(self, path_split: str, object_name: str = ''):
        super().__init__(self.exc_message.format(path_split=path_split), object_name)


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


class BinaryGeneratorException(LibException):
    pass


class InvalidDuplicateRangeException(LibException):
    def __init__(self, message, modified_settings=None):
        super().__init__(message)
        self.modified_settings = modified_settings if modified_settings is not None else []


class HashValidateException(LibException):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class MergeException(LibException):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class InternalBufferTooSmallException(LibException):
    exc_message = "Internal buffer of size {} is too small."

    def __init__(self, max_size):
        super().__init__(self.exc_message.format(max_size))
        self.max_size = max_size


class JSONException(LibException):
    def __init__(self, message):
        super().__init__(message)


class PathTooLongException(LibException):
    def __init__(self, message):
        super().__init__(message)


class FileException(LibException):
    exc_message: str = 'File error: {path}.'

    def __init__(self, path: str):
        self.path: str = path
        super().__init__(self.get_message(**self._message_args))

    @property
    def _message_args(self):
        return {'path': trim_user_input(self.path)}

    @classmethod
    def get_message(cls, **kwargs):
        return cls.exc_message.format(**kwargs)


class FileDoesNotExistException(FileException):
    exc_message = 'Given file does not exist: {path}.'


class DirectoryDoesNotExistException(FileDoesNotExistException):
    exc_message = 'Given directory does not exist: {path}.'


class OpenFileNoAccessException(FileException):
    exc_message = "Could not open file {path}. No read access."


class FileIsDirectory(FileException):
    exc_message = "Could not use {path}. Path points to a directory."


class BasenameTooLongException(FileException):
    exc_message = "Incorrect file {path}. Name is too long."


class SaveFileNoWriteAccessException(FileException):
    exc_message = 'Cannot write file into "{path}". No write access.'


class EmptyFileNameException(FileException):
    exc_message = 'Cannot write file into "{path}". File name cannot be empty'


class IncorrectFileTypeException(FileException):
    exc_message = 'Incorrect file type: "{path}". Must be one of: {accepted_types}.'

    def __init__(self, path: str, accepted_types: Iterable):
        self.accepted_types: Iterable[str] = accepted_types
        super().__init__(path)

    @property
    def _message_args(self):
        return {
            **super()._message_args,
            'accepted_types': ", ".join(self.accepted_types)
        }


class SaveFileException(FileException):
    exc_message = 'Cannot write file into "{path}". Make sure you have proper access and file is not used.'


class InvalidFilePathException(FileException):
    exc_message = 'Invalid file path: "{path}". The path contains non-ASCII or forbidden characters'\
                  f'\nEnsure the path only includes printable ASCII characters.'


class WrongTypeException(LibException):
    """Raised when object of wrong instance given."""


class SymlinkException(FileException):
    exc_message = 'Symlinks are not accepted ({path})'


class SecurityException(LibException):
    """Exception raised when the error message needs to be saved to security log."""


class XmlValidationFailedException(SecurityException):
    def __init__(self, xml_path: str, schema_path: str, error_message: str, line: int):
        super().__init__(
            f'Validation of file {xml_path} with schema {schema_path} failed at line {line}.\n{error_message}')


class SnapshotException(LibException):
    """Exception raised during processing configuration snapshots."""


class CustomActionException(LibException):
    """Exception raised during registering or processing custom actions."""
