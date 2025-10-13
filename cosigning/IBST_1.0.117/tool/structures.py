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

from os import urandom
from mmap import mmap
from enum import Enum
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from .LibException import LibException


class SupportedSHAs(object):
    class ShaType(Enum):
        Sha256 = "256"
        Sha512 = "512"

    shaClasses = {ShaType.Sha256: hashes.SHA256(),
                  ShaType.Sha512: hashes.SHA512()}


class SupportedPaddings(object):
    class PaddingSchemeType(Enum):
        pkcs1_v1_5 = "v1_5"
        pkcs1_pss = "PSS"

    paddingClasses = {PaddingSchemeType.pkcs1_v1_5: padding.PKCS1v15,
                      PaddingSchemeType.pkcs1_pss: padding.PSS}
    max_salt_len = padding.PSS.MAX_LENGTH

    @staticmethod
    def get_padding_args(salt_len, padding_type, sha_type):
        padding_args = {SupportedPaddings.PaddingSchemeType.pkcs1_v1_5: [],
                        SupportedPaddings.PaddingSchemeType.pkcs1_pss: [
                            padding.MGF1(SupportedSHAs.shaClasses[sha_type]),
                            salt_len]}
        return padding_args[padding_type]


class RsaKeyLength(Enum):
    Len2K = 1
    Len3K = 2


class RsaKeyType(Enum):
    Public = "Public"
    Private = "Private"


class ShaType(Enum):
    SHA256 = 1
    SHA512 = 2


class SigningKey:
    rsaKeyMapping = {RsaKeyLength.Len2K: 256,
                     RsaKeyLength.Len3K: 384}

    ExponentSize = 4

    def __init__(self):
        (self.modulus,
         self.public_exponent,
         self.private_exponent,
         self.prime_p,
         self.prime_q,
         self._rsa_key,
         self.hashed_key) = [0] * 7
        self.key_type = RsaKeyType.Public

    @property
    def rsa_key(self):
        return self._rsa_key

    @rsa_key.setter
    def rsa_key(self, value):
        self._rsa_key = value
        if isinstance(value, RSAPrivateKey):
            self.key_type = RsaKeyType.Private
        else:
            self.key_type = RsaKeyType.Public

    def sign(self, computed_hash, padding_algorithm, hash_algorithm):
        return self.rsa_key.sign(computed_hash, padding_algorithm, hash_algorithm)

    def verify(self, signature, computed_hash, padding_algorithm, hash_algorithm):
        if self.key_type == RsaKeyType.Private:
            key = self.rsa_key.public_key()
        else:
            key = self.rsa_key
        return key.verify(signature, computed_hash, padding_algorithm, hash_algorithm)

    @classmethod
    def get_key_len_type(cls, key):
        for key_type, length in cls.rsaKeyMapping.items():
            if length == len(key.modulus):
                return key_type
        return None

    @classmethod
    def get_key_len(cls, key_len):
        if key_len in cls.rsaKeyMapping:
            return cls.rsaKeyMapping[key_len]

        return None


class DataNode:
    nameTag = "name"
    valueTag = "value"
    pathTag = "path"
    startTag = "start"
    endTag = "end"

    name = None
    value = None
    path = None
    start = None
    end = None

    def __init__(self, xml_node):
        if self.nameTag in xml_node.attrib:
            self.name = xml_node.attrib[self.nameTag]
        if self.valueTag in xml_node.attrib:
            self.value = xml_node.attrib[self.valueTag]
        if self.pathTag in xml_node.attrib:
            self.path = xml_node.attrib[self.pathTag]
        if self.startTag in xml_node.attrib:
            self.start = xml_node.attrib[self.startTag]
        if self.endTag in xml_node.attrib:
            self.end = xml_node.attrib[self.endTag]

        if not self.value and not self.path and (not self.start or not self.end):
            raise LibException("Missing mandatory attributes '{}' or '{}' or '{}' and '{}'".
                               format(self.valueTag, self.pathTag, self.startTag, self.endTag))

    def check_start_end(self):
        if not self.start or not self.end:
            raise LibException("Missing mandatory attributes '{}' and '{}'".
                               format(self.startTag, self.endTag))

    def check_name(self):
        if not self.name:
            raise LibException("Missing mandatory attributes '{}'".
                               format(self.nameTag))


class AesEncryption:
    class Mode(Enum):
        ECB = 'ECB'
        CBC = 'CBC'
        CTR = 'CTR'

    ModeTypes = {Mode.ECB: 0,
                 Mode.CBC: 1,
                 Mode.CTR: 2}

    _PaddingTypes = None

    @classmethod
    def GetPaddingTypes(cls):
        if cls._PaddingTypes is None:
            cls._PaddingTypes = { cls.Mode.ECB : cls.Pkcs7Padding,
                                  cls.Mode.CBC : cls.ErrorPadding,
                                  cls.Mode.CTR : cls.NoPadding }
        return cls._PaddingTypes

    AesBlockSizeBytes = algorithms.AES.block_size // 8

    @classmethod
    def parse_mode(cls, modeStr):
        try:
            return cls.Mode(modeStr.upper())
        except Exception:
            values = [item.value for item in cls.Mode]
            raise LibException("Invalid name of encryption mode, choose one of: {}".
                               format(", ".join(values)))

    """
    mode instance must never be reused - when starting new encryption a new initialization vector
    of random data must be generated
    """
    @classmethod
    def get_mode_instance(cls, name, iv=None):
        if name == cls.Mode.ECB:
            return modes.ECB()
        if name == cls.Mode.CBC:
            return modes.CBC(iv if iv is not None else urandom(cls.AesBlockSizeBytes))
        if name == cls.Mode.CTR:
            return modes.CTR(iv if iv is not None else urandom(cls.AesBlockSizeBytes))
        raise LibException("There is no such encryption mode: {}".format(name))

    @classmethod
    def create_initialisation_vector(cls, mode_name):
        if mode_name == cls.Mode.CBC or mode_name == cls.Mode.CTR:
            return urandom(cls.AesBlockSizeBytes)
        return None

    @classmethod
    def get_empty_initialisation_vector(cls, mode_name):
        if mode_name == cls.Mode.CBC or mode_name == cls.Mode.CTR:
            return bytes([0] * cls.AesBlockSizeBytes)
        return None

    
    @classmethod
    def get_padding_instance(cls, encryption_mode):
        if encryption_mode not in cls.GetPaddingTypes():
            raise LibException(
                "There is no padding type defined for following encryption mode: {}".format(encryption_mode))
        return cls.GetPaddingTypes()[encryption_mode]()

    class Padding:
        def get_encrypted_data_size(self, data_size):
            raise LibException("Invalid padding - base class used")

        def calculate_padding_length(self, data_size):
            self.n_extra_bytes = data_size % AesEncryption.AesBlockSizeBytes
            self.padding_length = -data_size % AesEncryption.AesBlockSizeBytes
            self.n_full_blocks = data_size // AesEncryption.AesBlockSizeBytes

        def preencrypt(self, data):
            raise LibException("Invalid padding - base class used")

        def postencrypt(self, data):
            raise LibException("Invalid padding - base class used")

    class Cs1Padding(Padding):
        # For padding algorithm description see:
        # http://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a-add.pdf
        def get_encrypted_data_size(self, data_size):
            return data_size

        def preencrypt(self, data):
            self.calculate_padding_length(len(data))
            if self.n_full_blocks < 1:
                raise LibException("Invalid Length: must be at least {} (1 block size)".
                                   format(AesEncryption.AesBlockSizeBytes))

            return data + bytes([0] * self.padding_length)

        def postencrypt(self, data):
            part1 = data[:(self.n_full_blocks - 1) * AesEncryption.AesBlockSizeBytes +
                          self.n_extra_bytes]
            part2 = data[-AesEncryption.AesBlockSizeBytes:]
            return part1 + part2

    class Pkcs7Padding(Padding):
        def get_encrypted_data_size(self, data_size):
            self.calculate_padding_length(data_size)
            return data_size + self.padding_length

        def calculate_padding_length(self, data_size):
            super().calculate_padding_length(data_size)
            if self.padding_length == 0:
                self.padding_length = AesEncryption.AesBlockSizeBytes

        def preencrypt(self, data):
            self.calculate_padding_length(len(data))
            return data + bytes([self.padding_length] * self.padding_length)

        def postencrypt(self, data):
            return data

    class NoPadding(Padding):
        # For CTR mode we don't need any paddng
        def get_encrypted_data_size(self, data_size):
            return data_size

        def preencrypt(self, data):
            return data

        def postencrypt(self, data):
            return data

    class ErrorPadding(Padding):
        # This class doesn't allow any padding - data must be of proper size, otherwise an error is raised
        def get_encrypted_data_size(self, data_size):
            self.calculate_padding_length(data_size)
            if self.padding_length:
                raise LibException("Padding is disabled for this encryption mode, data must be aligned to {}. Use 'padding' attribute to align data size"
                                   .format(AesEncryption.AesBlockSizeBytes))
            return data_size

        def preencrypt(self, data):
            return data

        def postencrypt(self, data):
            return data


class Buffer(mmap):

    _error_message_pattern = "out of range"

    def __init__(self, file_no, length, **_):
        self._file_no = file_no
        self._max_size = length if length != 0 else self.size()

    def size(self):
        if self._file_no == -1:
            raise LibException(r"Cannot call 'size' method without an underlying file. Use 'max_size' property instead")
        return super().size()

    @property
    def max_size(self):
        return self._max_size

    def seek(self, *args, **kwargs):
        try:
            return super().seek(*args, **kwargs)
        except ValueError as e:
            if self._error_message_pattern in str(e):
                raise LibException("Internal buffer of size {} is too small: {}".format(self.max_size, str(e)))
            else:
                raise

    def write(self, *args, **kwargs):
        try:
            return super().write(*args, **kwargs)
        except ValueError as e:
            if self._error_message_pattern in str(e):
                raise LibException("Internal buffer of size {} is too small: {}".format(self.max_size, str(e)))
            else:
                raise

    def reduce_buffer_to_match_content(self):
        current_offset = self.tell()
        new_buffer = Buffer(self._file_no, current_offset)
        self.seek(0)
        content = self.read(current_offset)
        new_buffer.write(content)
        self.flush()
        self.close()
        return new_buffer
