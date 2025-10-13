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
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from ...ColorPrint import log
from ...FileManager import FileManager
from ...structures import SupportedSHAs
from .IFunction import IFunction
from ...LibException import ComponentException
from ...Converter import Converter


class HashFunction(IFunction):
    # pylint: disable=line-too-long
    """Used to hash given input data. There is one additional attribute 'legacy' that can be set to true in order
    to enable legacy hash algorithm (SHA-256), but it's not recommended to use it.

    Hash function configurable children:

    Configurable children   Required    Description
    ---------------------   --------    -----------
    sha                     yes         Indicates which hashing algorithm should be used (possible values are 256, 384, 512, which stand for SHA-256, SHA-384 and SHA-512)
    reverse                 no          Indicates if the output hash should be reversed (1 - reversed, 0 - normal, default is 0)
    save_hash               no          Indicates if hash should be saved to a separate file based on some *value* or *calculate* expression (default is false)
    save_hash_path          no          Indicates file path for the hash to be saved

    Here's an example which utilizes all of the configurable options and calculates a hash from given input file:

    ```xml
    <function_hash name="file_hash" legacy="false">
       <sha value="512"/>
       <reverse calculate="1"/>
       <input>
          <data path="/settings/input_file"/>
       </input>
       <save_hash calculate="/settings/output_hash_path.empty == False and /settings/save_hash.value == 1" />
       <save_hash_path calculate="/settings/output_hash_path.path" />
    </function_hash>
    ```

    Note: it's possible to add more than one 'data' node to any function input, then the data will be concatenated before performing calculations:

    ```xml
    <input>
        <data path="/settings/input_file"/>
        <data path="/layout/additional_data"/>
    </input>
    ```
    """
    # pylint: enable=line-too-long

    class Tags(IFunction.Tags):
        SAVE_HASH = "save_hash"
        SAVE_HASH_PATH = "save_hash_path"
        REVERSE = "reverse"
        DECRYPTED = "decrypted"

    sha_type = None
    sha_formula = None
    save_hash_formula = None
    save_hash = False
    save_hash_path_formula = None
    save_hash_path = None
    reverse_formula = None
    reverse = True
    sha = None

    @IFunction.size.getter
    def size(self):  # pylint: disable=invalid-overridden-method
        if self._size is None and self.sha_type is not None:
            return self.get_sha_size()
        return self._size

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        self._parse_sha(xml_node)
        self.save_hash_formula = self.parse_extra_node(xml_node, self.Tags.SAVE_HASH)
        self.save_hash_path_formula = self.parse_extra_node(xml_node, self.Tags.SAVE_HASH_PATH)
        self.reverse_formula = self.parse_extra_node(xml_node, self.Tags.REVERSE)

    def _parse_basic_attributes(self, xml_node):
        super()._parse_basic_attributes(xml_node)
        self._parse_legacy_attribute(xml_node)

    def _parse_sha(self, xml_node):
        sha_node = xml_node.find(self.Tags.SHA)
        if sha_node is None:
            self._raise_missing_child(self.Tags.SHA)

        try:
            if self.Tags.VALUE in sha_node.attrib:
                self.sha_formula = sha_node.attrib[self.Tags.VALUE]
                self.sha_type = SupportedSHAs.ShaType(sha_node.attrib[self.Tags.VALUE])
            elif self.Tags.CALCULATE in sha_node.attrib:
                self.sha_formula = sha_node.attrib[self.Tags.CALCULATE]
                sha_str = self.calculate_value(sha_node.attrib[self.Tags.CALCULATE])
                self.sha_type = SupportedSHAs.ShaType(sha_str)
            else:
                raise ComponentException(f"Missing value for tag: '{self.Tags.SHA}'", self.name)
        except ValueError:
            values = [item.value for item in SupportedSHAs.ShaType]
            raise ComponentException(f"Invalid value for '{self.Tags.SHA}' tag: '{sha_node.attrib[self.Tags.VALUE]}', "
                                     f"must be one of: {', '.join(values)}", self.name) from None

        if self.Tags.DECRYPTED in sha_node.attrib:
            decrypted = self.calculate_value(formula=sha_node.attrib[self.Tags.DECRYPTED], allow_calculate=True)
            if not isinstance(decrypted, bool):
                raise ComponentException(f"Invalid formula for '{self.Tags.DECRYPTED}' - result is not bool: "
                                         f"{sha_node.attrib[self.Tags.DECRYPTED]}", self.name)
            self.decrypted = decrypted

    def get_sha_size(self):
        return int(self.sha_type.value) // 8

    def get_sha(self, buffer=None):
        if self.sha is None:
            data = bytes(self.get_input_bytes(buffer))
            digest = hashes.Hash(SupportedSHAs.get_sha_class(self.sha_type, self.is_legacy), backend=default_backend())
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

        self.set_value(self.get_sha(buffer)[::-1] if self.reverse else self.get_sha(buffer))

        if self.save_hash and self.save_hash_path_formula:
            log().debug(f"{self.get_string_path()}: calculated hash:"
                        f"\n{Converter.bytes_to_string(self.get_sha(buffer))}")
            self.save_hash_path = self.calculate_value(formula=self.save_hash_path_formula)
            if not os.path.isabs(self.save_hash_path):
                self.save_hash_path = os.path.join(os.getcwd(), self.save_hash_path)
            FileManager.save_binary_file(self.save_hash_path, self.get_sha(buffer))
            log().debug(f"Hash was saved to {self.save_hash_path}\n")
