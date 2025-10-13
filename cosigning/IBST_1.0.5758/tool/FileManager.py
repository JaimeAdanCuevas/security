#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2022-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
import errno
import io
import os
import platform
import stat
from datetime import date
from typing import List
from pathlib import Path

from lxml.etree import tostring, Comment, ElementTree  # nosec - parsed xml is checked if there are no DOCTYPE elements. We don't use features that introduce other vulnerabilities

from .ColorPrint import log
from .FileOpener import open_file
from .LibConfig import LibConfig
from .LibException import FileDoesNotExistException, OpenFileNoAccessException, FileIsDirectory, \
    BasenameTooLongException, PathTooLongException, SaveFileNoWriteAccessException, SaveFileException, \
    EmptyFileNameException


class FileManager:
    """Class helping with work on files."""

    _copyright_text = """
    INTEL CONFIDENTIAL
    Copyright {} Intel Corporation.
    This software and the related documents are Intel copyrighted materials, and
    your use of them is governed by the express license under which they were
    provided to you (License).Unless the License provides otherwise, you may not
    use, modify, copy, publish, distribute, disclose or transmit this software or
    the related documents without Intel's prior written permission.

    This software and the related documents are provided as is, with no express or
    implied warranties, other than those that are expressly stated in the License.
    """

    @classmethod
    def copyright_text(cls):
        """Returns copyright text with current year."""
        return cls._copyright_text.format(date.today().year)

    @classmethod
    def create_dir_tree_if_absent(cls, path):
        """Checks if given path exists. If not, creates all missing directories and gives proper permissions."""
        if not path:
            return
        if not os.path.exists(path):
            dirs = cls.get_dirs_to_be_created(path) if LibConfig.toolType == LibConfig.ToolType.FIT else []
            os.makedirs(path)
            for directory in dirs:
                FileManager.set_linux_permissions(directory)

    @classmethod
    def existing_subpath(cls, path: str) -> str:
        """Returns a subpath ending with existing directory that's lowest in file hierarchy."""
        path = os.path.abspath(path)
        while not os.path.exists(path):
            new_path = os.path.split(path)[0]
            if path == new_path:
                # Could happen path to non existing drive given.
                # We can safely return empty string, as calling os.path.exists or os.access on one will always return
                # False. Just be careful to not convert it to absolute path before checking.
                return ''
            path = new_path
        return path

    @classmethod
    def get_dirs_to_be_created(cls, path: str) -> List:
        """Returns list of non-existing paths in given path."""
        result = []
        while path and path != '/' and not os.path.exists(path) and path not in result:
            result.insert(0, path)
            path = os.path.split(path)[0]
        return result

    @classmethod
    def validate_path(cls, path: str, *, for_saving: bool):
        if for_saving:
            cls.validate_path_to_save(path)
        else:
            cls.validate_path_to_open(path)

    @classmethod
    def validate_path_to_open(cls, path: str):
        """
        Checks if file under given path can be opened for reading.
        Raises exception if reading from file is not possible.
        """
        if not os.path.exists(path):
            raise FileDoesNotExistException(path)
        if not os.access(path, os.R_OK):
            raise OpenFileNoAccessException(path)

    @classmethod
    def validate_path_to_save(cls, path: str):
        """
        Checks if file under given path can be opened for writing.
        Raises exception if writing to file is not possible.
        """
        if os.name == "nt" and len(os.path.basename(path)) > 255:
            raise BasenameTooLongException(path)
        if os.path.exists(path):
            # File exists. Check if can be overwritten.
            if os.path.isdir(path):
                raise FileIsDirectory(path)
            if not os.access(path, os.W_OK):
                raise SaveFileNoWriteAccessException(path)
        else:
            # File does not exist. Check if directory has proper access.
            existing_path = cls.existing_subpath(os.path.split(path)[0])
            if not os.access(existing_path, os.X_OK | os.W_OK):
                raise SaveFileNoWriteAccessException(path)

    @classmethod
    def save_file(cls, path: str, data, flags: str):
        """
        Writes data to file. Creates directories if given path is missing. Sets proper file permissions.
        :param path: Path under which file should be saved.
        :param data: Data to be saved. Depending on flags can be string or binary (e.g. bytes)
        :param flags: Flags for open
        """
        try:
            path = cls.remove_whitespace_from_output_file(path)
            cls.create_dir_tree_if_absent(os.path.dirname(path))
            encoding = None if "b" in flags else 'utf-8'
            with open_file(path, flags, encoding=encoding) as file:
                file.write(data)
                if LibConfig.toolType == LibConfig.ToolType.FIT:
                    cls.set_linux_permissions(path)
        except (PermissionError, OSError, IOError, io.UnsupportedOperation) as exception:
            if cls._is_path_too_long_exception(path, exception):
                raise PathTooLongException(f'Path \"{path}\" length exceeds system limitation.') from exception
            raise SaveFileException(path) from exception

    @staticmethod
    def remove_whitespace_from_output_file(path: str):
        """
        Returns formatted output file path with removed whitespace(s) at the beginning of
        output file name if such exists.
        """
        file_path = Path(path)
        file_path_parts = file_path.parts
        file_name = file_path.name
        formatted_file_name = file_name.lstrip()
        if len(file_path_parts) > 1:
            new_file_path = os.path.join(str(file_path.parent), formatted_file_name)
        else:
            new_file_path = formatted_file_name
        if file_path != Path(new_file_path):
            log().warning(f"Unable to write output file with whitespace characters at the beginning. "
                          f"'{path}' will be updated to '{new_file_path}'")
            if not os.path.splitext(new_file_path)[1]:
                raise EmptyFileNameException(new_file_path)
        return new_file_path

    @staticmethod
    def _is_path_too_long_exception(path: str, exception: Exception) -> bool:
        """
        Determines if exception was raised, because of too long path to save a file.
        :param path: Path under which file should be saved.
        :param exception: Raised exception.
        """
        return len(path) > 255 and ((platform.system() == 'Windows' and isinstance(exception, FileNotFoundError))
                                    or (platform.system() == 'Linux' and isinstance(exception, OSError)
                                        and exception.errno == errno.ENAMETOOLONG))

    @classmethod
    def save_binary_file(cls, path: str, data):
        """Saves binary data as file under given path."""
        cls.save_file(path, data, 'wb')

    @classmethod
    def save_text_file(cls, path: str, text: str):
        """Saves text as file under given path."""
        cls.save_file(path, text, 'w')

    @classmethod
    def save_xml_file(cls, path: str, xml_node, include_copyright=False):
        """Saves xml node as text file under given path."""
        if include_copyright:
            xml_node.addprevious(Comment(cls.copyright_text()))
            xml_node = ElementTree(xml_node)
        xml_string = tostring(xml_node, pretty_print=True, xml_declaration=True, encoding="utf-8").decode("utf-8")
        cls.save_text_file(path, xml_string)

    @classmethod
    def set_linux_permissions(cls, path: str):
        """Removes all excessive permissions from file under given path."""
        if os.name == "nt":  # on Windows we skip this
            return
        # Get current permission mask.
        st_mode = os.stat(path).st_mode

        st_mode &= ~stat.S_IWOTH  # Remove WRITE permission fot Others
        st_mode &= ~(stat.S_ISUID | stat.S_ISGID)  # Remove SPECIAL permission bit for User on Group
        if not os.path.isdir(path):
            st_mode &= ~stat.S_IXOTH  # Remove EXECUTE permission for Others
        os.chmod(path, st_mode)
