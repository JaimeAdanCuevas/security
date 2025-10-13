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

from .IComponent import IComponent
from ..LibException import LibException
from .. import utils as utils
from ..structures import ShaType
from ..utils import validate_file
from ..LibConfig import LibConfig
from ..Converter import Converter


class RsaKeyComponent(IComponent):
    hashTypeTag = "hash_type"
    hashAlgorithms = {"sha256": ShaType.SHA256,
                      "sha512": ShaType.SHA512}
    requiredTag = "required"

    class ComponentProperty(Enum):
        Modulus = "modulus"
        Exponent = "exponent"
        HashedKey = "hashed_key"
        SignatureSize = "signature_size"
        Empty = "empty"

    key = None
    hash_type = None
    required = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self._reload_key()
        if LibConfig.is_verbose:
            print(self.name)
            utils.hashed_key_printer(self.key, None)
            print("")

    def _parse_string_value(self, value):
        self._parse_string_path_value(value, self.required)
        self._reload_key()
        return self.value

    def _reload_key(self):
        if self.error_message is not None or not self.value:
            return

        self.key = utils.process_key_file(self.value, self.hash_type)

    def _parse_additional_attributes(self, xml_node):
        self.required = Converter.string_to_bool(self._parse_attribute(xml_node, self.requiredTag, False, 'true'))
        self.parse_hash_type(xml_node)
        
    def parse_hash_type(self, xml_node):

        if self.hashTypeTag in xml_node.attrib:
            value = xml_node.attrib[self.hashTypeTag]
            if value in self.hashAlgorithms:
                self.hash_type = self.hashAlgorithms[value]
            else:
                self.hash_type = None
        else:
            self.hash_type = ShaType.SHA256

    def validate(self):
        super().validate()

        if not self.value:
            return
        try:
            validate_file(self.value)
        except LibException as ex:
            self.error_message = str(ex)
            return

    def _get_property(self, component_property, _=False):
        if component_property == self.ComponentProperty.Empty:
            if not self.value:
                return True
            return False
        self._check_error()
        if component_property == self.ComponentProperty.Modulus:
            return self.key.modulus
        if component_property == self.ComponentProperty.Exponent:
            return self.key.public_exponent
        if component_property == self.ComponentProperty.HashedKey:
            return self.key.hashed_key
        if component_property == self.ComponentProperty.SignatureSize:
            return len(self.key.modulus)

    def sign(self, computed_hash, padding_algorithm, hash_algorithm):
        return self.key.sign(computed_hash, padding_algorithm, hash_algorithm)

    def encrypt(self, _, __):
        raise LibException("Encryption with RSA key is not supported")

    def _copy_to(self, dst):
        super()._copy_to(dst)
        dst.key = self.key
        dst.hash_type = self.hash_type
