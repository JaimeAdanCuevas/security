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

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

from enum import Enum
from ...LibException import ComponentException
from .IFunction import IFunction
from ...structures import SupportedSHAs, SupportedPaddings


class VerifyFunction(IFunction):
    hashTag = "hash"
    keyTag = "custom_key"
    signatureTag = "signature"

    class KeyData(Enum):
        sizeTag = "size"
        exponentTag = "exponent"
        modulusTag = "modulus"

    data = {}
    hash_path = None
    hash = None
    key = None
    signature_to_verify = None

    def parse_children(self, xml_node, buffer = None):
        self.data[self.hashTag] = self._parse_component(xml_node, self.hashTag)
        self.data[self.signatureTag] = self._parse_component(xml_node, self.signatureTag)
        self._parse_key_tag(xml_node)

    def _parse_key_tag(self, xml_node):
        key_node = xml_node.find(self.keyTag)
        if key_node is None:
            self._raise_missing_child(self.keyTag)
        for e in self.KeyData:
            comp_data = self._parse_component(key_node, e.value)
            self.data[e] = comp_data

    def _parse_component(self, key_node, tag):
        key_comp_node = key_node.find(tag)
        key_comp_data = {}
        if key_comp_node is None:
            self._raise_missing_child(tag)
        key_comp_data[self.valueTag] = key_comp_node.attrib[self.valueTag]
        if self.orderTag in key_comp_node.attrib:
            order_cont = key_comp_node.attrib[self.orderTag]
        else:
            order_cont = self.bigOrder
        key_comp_data[self.orderTag] = order_cont
        return key_comp_data

    def _build_layout(self):
        key_size = self.calculate_value_from_path(self.data[self.KeyData.sizeTag][self.valueTag])
        exponent = self.calculate_value_from_path(self.data[self.KeyData.exponentTag][self.valueTag])
        modulus = self.calculate_value_from_path(self.data[self.KeyData.modulusTag][self.valueTag])
        self._construct_key(key_size, exponent, modulus)
        self.set_size(self.key.key_size // 8)
        self._set_value(b'\0' * self.data_size)
        self.hash = self.calculate_value_from_path(self.data[self.hashTag][self.valueTag])
        self.signature = self.calculate_value_from_path(self.data[self.signatureTag][self.valueTag])
        self.signature = bytearray(self.signature[:self.data_size])
        if self.data[self.signatureTag][self.orderTag] == self.littleOrder:
            self.signature.reverse()

    def _build(self, buffer):
        self._set_value(self.signature)

        for padding in SupportedPaddings.PaddingSchemeType:
            padding_args = SupportedPaddings.get_padding_args(SupportedPaddings.max_salt_len, padding,
                                                              self.hash.sha_type)
            padding_class = SupportedPaddings.paddingClasses[padding]
            if self._verify(padding_class(*padding_args)):
                return

        raise ComponentException("Verification failure!", self.name)

    def _verify(self, padding_class):
        try:
            self.key.verify(
                bytes(self.signature),
                self.hash.get_sha(),
                padding_class,
                utils.Prehashed(SupportedSHAs.shaClasses[self.hash.sha_type]))
        except InvalidSignature as e:
            return False

        print("Verification succeeded!")
        return True

    def _construct_key(self, size, e, n):
        size = int.from_bytes(size, self.data[self.KeyData.sizeTag][self.orderTag]) // 8
        e = int.from_bytes(e, self.data[self.KeyData.exponentTag][self.orderTag])
        n = n[:size]
        n = int.from_bytes(n, self.data[self.KeyData.modulusTag][self.orderTag])
        try:
            key = rsa.RSAPublicNumbers(e, n)
            self.key = key.public_key(backend=default_backend())
        except ValueError as e:
            raise ComponentException("Cannot create RSA key from given data!", self.name)
