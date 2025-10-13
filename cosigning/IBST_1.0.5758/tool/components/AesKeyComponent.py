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

from enum import Enum
from typing import List

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend

from ..FileManager import FileManager
from ..FileOpener import open_file
from .IComponent import IComponent
from ..LibException import LibException, ComponentException, FileException
from ..PropertyState import ComponentPreChangeState
from ..utils import hashed_key_printer
from ..structures import AesEncryption
from ..LibConfig import LibConfig


class AesKeyComponent(IComponent):
    """Represents an AES key. Recommended key size is 256, but key size 128 can be enabled through setting
    special legacy attribute to true. Value for this setting should be a path to key file (can be left empty).

    Aes key special properties

    Special property    Description
    ----------------    -----------
    key                 Gets the key
    encryption_type     Gets the encryption type (128 or 256)
    """

    # encryptionTypes maps AES key length to value that should be put into generated binary - don't change
    encryptionTypes = {None: 0,
                       AesEncryption.KeyLength.AES128: 1,
                       AesEncryption.KeyLength.AES256: 2, }

    class ComponentProperty(Enum):
        KEY = "key"
        ENCRYPTION_TYPE = "encryption_type"
        ENABLED = "enabled"

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)

        self._key = None
        self._key_length = None

    @property
    def key(self):
        if self._key is None:
            self._parse_key()
        return self._key

    @property
    def key_length(self):
        if self._key_length is None:
            self._parse_key()
        return self._key_length

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        self._key = None  # lazy reloading
        self._key_length = None  # lazy reloading
        return super().parse_string_value(value)

    def get_parsed_string_value(self, value):
        return value

    def _parse_basic_attributes(self, xml_node):
        super()._parse_basic_attributes(xml_node)
        self._parse_legacy_attribute(xml_node)

    @staticmethod
    def _parse_key_from_file(path):
        with open_file(path, 'rb') as file:
            return file.read()

    def _parse_key(self):
        if not self.is_enabled():
            self._key = bytes([])
            return

        try:
            FileManager.validate_path_to_open(self.value)
        except FileException as ex:
            raise ComponentException(ex.message, self.display_name) from None

        self._key = self._parse_key_from_file(self.value)
        self._key_length = self._calc_key_length(self._key)

        if LibConfig.isVerbose or LibConfig.toolType == LibConfig.ToolType.IBST:
            print(self.name)
            hashed_key_printer(self._key, None)
            print("")

    def _calc_key_length(self, key):
        return AesEncryption.get_key_length_type(len(key) * 8, self.is_legacy)

    def _get_property(self, component_property, _=False, report_usage=False):
        if report_usage:
            self.set_data_used_for_building(report_usage)
        self._check_error()
        if component_property == self.ComponentProperty.KEY:
            return self.key
        if component_property == self.ComponentProperty.ENCRYPTION_TYPE:
            return self.encryptionTypes[self.key_length]
        if component_property == self.ComponentProperty.ENABLED:
            return self.is_enabled()
        return None

    def _should_omit_parsing(self, xml_node):
        # We never want to skip parsing AesKeyComponent but we need initialisation
        # which is done in this method
        super()._should_omit_parsing(xml_node)
        return False

    def get_encrypted_data_size(self, data_size, encryption_mode_name):
        try:
            padding = AesEncryption.get_padding_instance(encryption_mode_name)
        except LibException as e:
            raise ComponentException(str(e), self.name) from None

        encrypted_data_size = padding.get_encrypted_data_size(data_size)
        return encrypted_data_size

    def encrypt(self, data, encryption_mode_name, iv=None):
        self._check_error()
        mode = AesEncryption.get_mode_instance(encryption_mode_name, iv)
        padding = AesEncryption.get_padding_instance(encryption_mode_name)
        cipher = Cipher(algorithms.AES(self.key),
                        mode,
                        backend=default_backend())
        encryptor = cipher.encryptor()

        try:
            data = bytes(padding.preencrypt(data))
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            encrypted_data = padding.postencrypt(encrypted_data)
        except Exception as e:
            raise ComponentException(str(e), self.name) from None

        return encrypted_data

    def _copy_to(self, dst):
        super()._copy_to(dst)
        # pylint: disable=protected-access
        dst._key = self._key
        dst._key_length = self._key_length
        # pylint: enable=protected-access
