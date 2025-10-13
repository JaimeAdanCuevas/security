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
from ..utils import validate_file
from ..structures import AesEncryption


class AesKeyComponent(IComponent):

    class KeyLength(Enum):
        Aes128 = 128
        Aes256 = 256

    """
    encryptionTypes maps AES key length to value that should be put into generated binary - don't change
    """
    encryptionTypes = { None : 0,
                        KeyLength.Aes128 : 1,
                        KeyLength.Aes256 : 2, }

    class ComponentProperty(Enum):
        Key = "key"
        EncryptionType = "encryption_type"
        Enabled = "enabled"

    key = None
    key_length = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)

        if self.error_message is not None:
            return

        if not self._is_enabled():
            self.key = bytes([])
            return

        try:
            self.parse_key()
        except LibException as e:
            self.error_message = str(e)
            return

        self.validate_key()

    def _parse_string_value(self, value):
        self._parse_string_path_value(value)
        return self.value

    @staticmethod
    def parse_key_from_file(path):
        with open(path, 'rb') as file:
            return file.read()

    def parse_key(self):
        self.key = self.parse_key_from_file(self.value)
        try:
            self.key_length = self.KeyLength(len(self.key) * 8)
        except ValueError as e:
            raise LibException("Invalid key length: {} ({})".format(len(self.key), str(e)))

    def validate(self):
        super().validate()

        if not self._is_enabled():
            return

        if not self.value:
            self.error_message = "Path to the key file was not specified"
            return
        try:
            validate_file(self.value)
        except LibException as ex:
            self.error_message = str(ex)
            return

    def validate_key(self):
        if self.key is None:
            self.error_message = "AES key for '{}' was not specified".format(self.name)

    def _get_property(self, component_property, _=False):
        self._check_error()
        if component_property == self.ComponentProperty.Key:
            return self.key
        if component_property == self.ComponentProperty.EncryptionType:
            return self.encryptionTypes[self.key_length]
        if component_property == self.ComponentProperty.Enabled:
            return self._is_enabled()

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
        dst.key = self.key
        dst.key_length = self.key_length
