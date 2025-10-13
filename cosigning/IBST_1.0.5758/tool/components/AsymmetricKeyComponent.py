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
from re import search

from .FileComponent import FileComponent
from ..LibException import LibException, ComponentException
from .. import utils
from ..PropertyState import ComponentPreChangeState
from ..structures import RsaSigningKey, AsymmetricKeyType, SupportedSHAs, EcSigningKey
from ..LibConfig import LibConfig


class AsymmetricKeyComponent(FileComponent):
    """Represents an asymmetric key - either RSA or elliptic.
    The key can be used, for example, for signing or hashing purposes.
    Value for this settings should be a path to key file (can be left empty).

    Asymmetric key special properties

    Special property    Description
    ----------------    -----------
    modulus             Gets the public key modulus (only for RSA)
    exponent            Gets the public key exponent (only for RSA)
    hashed_key          Gets the hashed key
    signature_size      Gets the signature size depending on given key
    type_rsa            Returns 1 if key is an RSA type key, otherwise returns 0
    qx                  Gets public key x (only for ECC)
    qy                  Gets public key y (only for ECC)
    signature_s         Gets the signature S (only for ECC)
    signature_r         Gets the signature R (only for ECC)
    coordinate_size     Gets the key coordinate
    is_private          Returns 1 if key is a private key, otherwise returns 0
    curve               Gets the key curve
    """

    class Tags(FileComponent.Tags):
        HASH_TYPE = "hash_type"

    shaPrefix = "sha"

    class ComponentProperty(Enum):
        MODULUS = "modulus"
        EXPONENT = "exponent"
        HASHED_KEY = "hashed_key"
        SIGNATURE_SIZE = "signature_size"
        TYPE_RSA = "type_rsa"
        QX = "qx"
        QY = "qy"
        COORDINATE_SIZE = "coordinate_size"
        EMPTY = "empty"
        PRIVATE = "is_private"
        SIGNATURE_S = 'signature_s'
        SIGNATURE_R = 'signature_r'
        CURVE = 'curve'

    class KeyType(Enum):
        EC = 0
        RSA = 1

    hash_type = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self._key = None

    @property
    def key(self):
        if self._key is None:
            self._reload_key()
        return self._key

    @property
    def is_private(self):
        return self.key.key_type == AsymmetricKeyType.PRIVATE

    @property
    def key_type(self):
        return self.KeyType.EC if isinstance(self.key, EcSigningKey) else self.KeyType.RSA

    @property
    def key_size(self):
        if isinstance(self.key, RsaSigningKey):
            return len(self.key.modulus)

        if isinstance(self.key, EcSigningKey):
            size = search("\\d{3}", self.key.curve)
            return int(size.group())

        raise LibException("Unexpected error: unknown key type detected, cannot get the size.")

    @classmethod
    def key_type_from_header(cls, header: int):
        if EcSigningKey.is_ec_header(header):
            return cls.KeyType.EC
        return cls.KeyType.RSA

    def parse_string_value(self, value) -> List[ComponentPreChangeState]:
        self._key = None  # lazy reloading
        return super().parse_string_value(value)

    def get_parsed_string_value(self, value):
        return value

    def _reload_key(self):
        super()._validate_file()

        try:
            self._key = utils.process_key_file(self.value, self.hash_type, True)
        except LibException as e:
            raise ComponentException(f"Could not parse key: {self.value}\n" + str(e), self.display_name) from None

        if LibConfig.isVerbose or LibConfig.toolType == LibConfig.ToolType.IBST:
            print(self.name)
            utils.hashed_key_printer(self._key, None)
            print("")

    def _parse_additional_attributes(self, xml_node):
        super()._parse_additional_attributes(xml_node)
        self._parse_hash_type(xml_node)

    def _parse_hash_type(self, xml_node):
        if self.Tags.HASH_TYPE in xml_node.attrib:
            hash_name: str = xml_node.attrib[self.Tags.HASH_TYPE]
            if not hash_name.startswith(self.shaPrefix):
                hash_name = self.shaPrefix + hash_name
            self.hash_type = SupportedSHAs.get_sha_type(hash_name)
        else:
            self.hash_type = SupportedSHAs.ShaType.SHA256

    def _get_property(self, component_property, _=False, report_usage=False):
        if report_usage:
            self.set_data_used_for_building(report_usage)
        if component_property == self.ComponentProperty.EMPTY:
            if not self.value:
                return True
            return False
        self._check_error()
        self._validate_property(component_property)
        if component_property == self.ComponentProperty.MODULUS:
            return self.key.modulus
        if component_property == self.ComponentProperty.EXPONENT:
            return self.key.public_exponent
        if component_property == self.ComponentProperty.HASHED_KEY:
            return self.key.hashed_key
        if component_property == self.ComponentProperty.SIGNATURE_SIZE:
            if isinstance(self.key, RsaSigningKey):
                return len(self.key.modulus)
            if isinstance(self.key, EcSigningKey):
                return len(self.key.qx) + len(self.key.qy)
        if component_property == self.ComponentProperty.TYPE_RSA:
            return isinstance(self.key, RsaSigningKey)
        if component_property == self.ComponentProperty.QX:
            return self.key.qx
        if component_property == self.ComponentProperty.QY:
            return self.key.qy
        if component_property == self.ComponentProperty.COORDINATE_SIZE:
            return self.key.coordinate_size
        if component_property == self.ComponentProperty.PRIVATE:
            return self.key.key_type == AsymmetricKeyType.PRIVATE
        if component_property == self.ComponentProperty.SIGNATURE_S:
            return self.key.signature_s
        if component_property == self.ComponentProperty.SIGNATURE_R:
            return self.key.signature_r
        if component_property == self.ComponentProperty.CURVE:
            return self.key.curve if isinstance(self.key, EcSigningKey) else ''
        return None

    def _validate_property(self, component_property):
        if not isinstance(self.key, RsaSigningKey) and not isinstance(self.key, EcSigningKey):
            raise ComponentException("Unsupported key type", self.name)
        if component_property == self.ComponentProperty.MODULUS and isinstance(self.key, EcSigningKey):
            raise ComponentException(f"Cannot get modulus of elliptic key: '{self.name}'. "
                                     "RSA key must be given.")
        if component_property == self.ComponentProperty.EXPONENT and isinstance(self.key, EcSigningKey):
            raise ComponentException(f"Cannot get exponent of elliptic key: '{self.name}'. "
                                     "RSA key must be given.")
        if component_property == self.ComponentProperty.QX and isinstance(self.key, RsaSigningKey):
            raise ComponentException(f"Cannot get qx attribute of RSA key: '{self.name}'. "
                                     "Elliptic key must be given.")
        if component_property == self.ComponentProperty.QY and isinstance(self.key, RsaSigningKey):
            raise ComponentException(f"Cannot get qy attribute of RSA key: '{self.name}'. "
                                     "Elliptic key must be given.")
        if component_property == self.ComponentProperty.SIGNATURE_S and isinstance(self.key, RsaSigningKey):
            raise ComponentException(f"Cannot get signature_s attribute of RSA key: '{self.name}'. "
                                     "Elliptic key must be given.")
        if component_property == self.ComponentProperty.SIGNATURE_R and isinstance(self.key, RsaSigningKey):
            raise ComponentException(f"Cannot get signature_r attribute of RSA key: '{self.name}'. "
                                     "Elliptic key must be given.")

    def sign(self, computed_hash, padding_algorithm, hash_algorithm, reverse):
        return self.key.sign(computed_hash, padding_algorithm, hash_algorithm, reverse)

    def verify(self, signature, computed_hash, padding_algorithm, hash_algorithm, reverse=False):
        return self.key.verify(bytes(signature), computed_hash, padding_algorithm, hash_algorithm, reverse)

    def encrypt(self, _, __):
        raise LibException("Encryption with RSA key is not supported")

    def _copy_to(self, dst):
        super()._copy_to(dst)
        # pylint: disable=protected-access
        dst._key = self._key
        dst.hash_type = self.hash_type
        dst._data_used_for_building = self._data_used_for_building
        # pylint: enable=protected-access

    def formatted_key_type(self):
        return self.key_type.name.upper() + self.key.formatted_key_type()
