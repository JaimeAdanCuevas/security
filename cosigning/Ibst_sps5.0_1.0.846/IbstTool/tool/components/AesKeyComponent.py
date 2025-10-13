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

from enum import Enum
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend

from .IComponent import IComponent
from ..LibException import LibException, ComponentException
from ..utils import validate_file, hashed_key_printer
from ..structures import AesEncryption
from ..LibConfig import LibConfig


class AesKeyComponent(IComponent):
    class KeyLength(Enum):
        Aes128 = 128
        Aes256 = 256

    """
    encryptionTypes maps AES key length to value that should be put into generated binary - don't change
    """
    encryptionTypes = {None: 0,
                       KeyLength.Aes128: 1,
                       KeyLength.Aes256: 2, }

    class ComponentProperty(Enum):
        Key = "key"
        EncryptionType = "encryption_type"
        Enabled = "enabled"

    key_length = None

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

    def _parse_string_value(self, value):
        self._set_value(value)
        self._key = None  # lazy reloading
        self._key_length = None  # lazy reloading
        return self.value

    @staticmethod
    def _parse_key_from_file(path):
        with open(path, 'rb') as file:
            return file.read()

    def _parse_key(self):
        if not self._is_enabled():
            self._key = bytes([])
            return

        validate_file(self.value)

        self._key = self._parse_key_from_file(self.value)
        self._key_length = self._calc_key_length(self._key)

        if LibConfig.is_verbose:
            print(self.name)
            hashed_key_printer(self._key, None)
            print("")

    def _calc_key_length(self, key):
        try:
            length = self.KeyLength(len(key) * 8)
        except ValueError as e:
            raise LibException("Invalid key length: {} ({})".format(len(key), str(e)))
        return length

    def _get_property(self, component_property, _=False):
        self._check_error()
        if component_property == self.ComponentProperty.Key:
            return self.key
        if component_property == self.ComponentProperty.EncryptionType:
            return self.encryptionTypes[self.key_length]
        if component_property == self.ComponentProperty.Enabled:
            return self._is_enabled()

    def _should_omit_parsing(self, xml_node):
        # We never want to skip parsing AesKeyComponent but we need initialisation
        # which is done in this method
        super()._should_omit_parsing(xml_node)
        return False

    def get_encrypted_data_size(self, data_size, encryption_mode_name):
        try:
            padding = AesEncryption.get_padding_instance(encryption_mode_name)
        except LibException as e:
            raise ComponentException(str(e), self.name)

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
            raise ComponentException(str(e), self.name)

        return encrypted_data

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst._key = self._key
        dst._key_length = self._key_length
