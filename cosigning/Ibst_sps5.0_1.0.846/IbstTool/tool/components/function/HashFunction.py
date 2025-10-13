#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2017-2020 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from ...structures import SupportedSHAs
from .IFunction import IFunction
from ...LibException import ComponentException
from ...Converter import Converter
from ...LibConfig import LibConfig


class HashFunction(IFunction):
    shaTag = "sha"
    saveHashTag = "save_hash"
    saveHashPathTag = "save_hash_path"
    reverseTag = "reverse"
    decryptedTag = "decrypted"

    sha_type = None
    save_hash_formula = None
    save_hash = False
    save_hash_path_formula = None
    save_hash_path = None
    reverse_formula = None
    reverse = True
    sha = None

    @IFunction.size.getter
    def size(self):
        if self._size is None and self.sha_type is not None:
            return self.get_sha_size()
        return self._size

    def parse_children(self, xml_node, buffer=None):
        super().parse_children(xml_node)
        self._parse_sha(xml_node)
        self.save_hash_formula = self.parse_extra_node(xml_node, self.saveHashTag)
        self.save_hash_path_formula = self.parse_extra_node(xml_node, self.saveHashPathTag)
        self.reverse_formula = self.parse_extra_node(xml_node, self.reverseTag)

    def _parse_sha(self, xml_node):
        sha_node = xml_node.find(self.shaTag)
        if sha_node is None:
            self._raise_missing_child(self.shaTag)

        try:
            if self.valueTag in sha_node.attrib:
                self.sha_type = SupportedSHAs.ShaType(sha_node.attrib[self.valueTag])
            elif self.calculateTag in sha_node.attrib:
                sha_str = self.calculate_value(sha_node.attrib[self.calculateTag])
                self.sha_type = SupportedSHAs.ShaType(sha_str)
            else:
                raise ComponentException("Missing value for tag: '{}'".format(self.shaTag), self.name)
        except ValueError:
            values = [item.value for item in SupportedSHAs.ShaType]
            raise ComponentException("Invalid value for '{}' tag: '{}', must be one of: {}"
                                     .format(self.shaTag, sha_node.attrib[self.valueTag], ", "
                                             .join(values)),
                                     self.name)

        if self.decryptedTag in sha_node.attrib:
            decrypted = self.calculate_value(formula=sha_node.attrib[self.decryptedTag],
                                                         allow_calculate=True)
            if not isinstance(decrypted, bool):
                raise ComponentException("Invalid formula for '{}' - result is not bool: {}".
                                         format(self.decryptedTag, sha_node.attrib[self.decryptedTag]), self.name)
            self.decrypted = decrypted

    def get_sha_size(self):
        return int(int(self.sha_type.value) / 8)

    def get_sha(self):
        if self.sha is None:
            data = bytes(self.get_input_bytes())
            digest = hashes.Hash(SupportedSHAs.shaClasses[self.sha_type], backend=default_backend())
            digest.update(data)
            self.sha = digest.finalize()

        return self.sha

    def get_default_value(self):
        return b'\0' * (self.get_sha_size() if self.size is None else self.size)

    def _build_layout(self):
        super()._build_layout()
        self.size = self.get_sha_size()

    def _build(self, buffer):
        super()._build(buffer)

        if self.save_hash_formula:
            self.save_hash = self.calculate_value(formula=self.save_hash_formula)

        if self.reverse_formula:
            self.reverse = self.calculate_value(formula=self.reverse_formula)

        self._set_value(self.get_sha()[::-1] if self.reverse else self.get_sha())

        if self.save_hash and self.save_hash_path_formula:
            if LibConfig.is_verbose:
                print("{}: calculated hash:\n{}".
                    format(self.get_string_path(), Converter.bytes_to_string(self.get_sha())))
            self.save_hash_path = self.calculate_value(formula=self.save_hash_path_formula)
            with open(self.save_hash_path, 'wb') as f:
                f.write(self.get_sha())
            if LibConfig.is_verbose:
                print("Hash was saved to {}\n".format(self.save_hash_path))
