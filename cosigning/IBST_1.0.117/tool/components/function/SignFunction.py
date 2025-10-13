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

import subprocess
import os
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import utils
from ...LibException import ComponentException
from .HashFunction import HashFunction
from ...structures import SupportedSHAs, SupportedPaddings, RsaKeyType


class SignFunction(HashFunction):
    keyTag = "key"
    paddingSchemeTag = "padding_scheme"
    paddingSaltLenAttrTag = "salt_len"
    signingUtilTag = "signing_utility"
    loadExternalDataTag = "load_external_data"
    externalDataTag = "external_data"
    offlineSigningTag = "offline_signing"

    key_path = None
    key = None
    padding_scheme = SupportedPaddings.PaddingSchemeType.pkcs1_v1_5
    signing_script_path = None
    signing_script = None
    salt_len = SupportedPaddings.max_salt_len
    load_external_data_formula = None
    load_external_data = False
    external_data_formula = None
    external_data = None
    offline_signing_formula = None
    offline_signing = False

    def parse_children(self, xml_node, buffer = None):
        super().parse_children(xml_node, buffer)
        self._parse_key_tag(xml_node)
        self._parse_signing_utility_tag(xml_node)
        self.load_external_data_formula = self.parse_extra_node(xml_node, self.loadExternalDataTag)
        self.external_data_formula = self.parse_extra_node(xml_node, self.externalDataTag)
        self.offline_signing_formula = self.parse_extra_node(xml_node, self.offlineSigningTag)

    def _parse_key_tag(self, xml_node):
        key_node = self._parse_node(xml_node, self.keyTag)

        if self.valueTag not in key_node.attrib:
            raise ComponentException("Missing value for tag: '{}'".format(self.keyTag), self.name)

        self.key_path = key_node.attrib[self.valueTag]

        padding_scheme_node = xml_node.find(self.paddingSchemeTag)
        if padding_scheme_node is not None:
            if self.valueTag not in padding_scheme_node.attrib:
                raise ComponentException("Missing value for tag: '{}'"
                                         .format(self.paddingSchemeTag), self.name)
            padding_scheme_string = padding_scheme_node.attrib[self.valueTag]
            allowed_padding_schemes = [e.value for e in SupportedPaddings.PaddingSchemeType]
            if padding_scheme_string in allowed_padding_schemes:
                padding_scheme_value = padding_scheme_string
            else:
                calculate_exception = None
                try:
                    padding_scheme_value = self.calculate_value(padding_scheme_string, allow_calculate=True)
                except ComponentException as ex:
                    calculate_exception = ex
                if calculate_exception or padding_scheme_value not in allowed_padding_schemes:
                    raise ComponentException("Invalid value for '{}', use one of: '{}'{}"
                                             .format(self.paddingSchemeTag,
                                                     ", ".join(allowed_padding_schemes),
                                                     ", " + str(calculate_exception) if calculate_exception else ""),
                                             self.name)
            self.padding_scheme = SupportedPaddings.PaddingSchemeType(padding_scheme_value)
            if self.paddingSaltLenAttrTag not in padding_scheme_node.attrib:
                raise ComponentException("Missing salt_len tag: '{}'"
                                         .format(self.paddingSaltLenAttrTag), self.name)
            if padding_scheme_node.attrib[self.paddingSaltLenAttrTag]:
                try:
                    self.salt_len = self.calculate_value(padding_scheme_node.attrib[self.paddingSaltLenAttrTag],
                                                         allow_calculate=True)
                except (ValueError, TypeError, ComponentException):
                    raise ComponentException(
                        "Incorrect salt_len: {}".format(padding_scheme_node.attrib[self.paddingSaltLenAttrTag]),
                        self.name)

    def _parse_signing_utility_tag(self, xml_node):
        signing_util_node = xml_node.find(self.signingUtilTag)

        if signing_util_node is None:
            raise ComponentException("Missing mandatory child for tag: '{}'"
                                     .format(self.signingUtilTag), self.name)

        if self.valueTag in signing_util_node.attrib:
            self.signing_script = signing_util_node.attrib[self.valueTag]
        else:
            self.signing_script_path = signing_util_node.attrib[self.calculateTag]

    def sign_external(self):
        data_file_name = 'data_to_sign.bin'
        signature_file_name = 'signature.bin'
        sha_arg = "sha" + self.sha_type.value

        with open(data_file_name, 'wb') as file:
            file.write(self.get_input_bytes())

        absIn = os.path.abspath(data_file_name)
        absPath = os.path.dirname(absIn)
        absOut = os.path.join(absPath, signature_file_name)

        cmd = 'python {} {} {} {} {}'.format(self.signing_script,
                                             sha_arg,
                                             self.key.value,
                                             absOut,
                                             absIn)

        try:
            print('Calling external signing script: "{}"'.format(cmd))
            subprocess.check_call(cmd, shell=True, timeout=60)
        except subprocess.CalledProcessError as e:
            raise ComponentException("Problem calling signing script '{}': {}"
                                     .format(self.signing_script, e.returncode), self.name)
        except subprocess.TimeoutExpired:
            raise ComponentException("Timeout (60s) occurred while calling signing script '{}'"
                                     .format(self.signing_script), self.name)

        try:
            with open(signature_file_name, 'rb') as file:
                signature = file.read()
        except FileNotFoundError as ex:
            raise ComponentException("Cannot open calculated signature. {}: {}"
                                     .format(ex.strerror, ex.filename), self.name)

        return signature[::-1]

    def _build_layout(self):
        self.key = self.calculate_value(self.key_path, allow_calculate = True)
        self.set_size(self.key.get_property("signature_size"))
        self._set_value(b'\0' * self.data_size)
        if self.signing_script_path:
            self.signing_script = self.calculate_value_from_path(self.signing_script_path).value

    def _build(self, buffer):
        super()._build(buffer)

        if self.offline_signing_formula:
            self.offline_signing = self.calculate_value(formula=self.offline_signing_formula)

        if self.offline_signing:
            print("{}:\nOffline signing - signature will NOT be computed!\n".format(self.get_string_path()))

            if self.load_external_data_formula:
                self.load_external_data = self.calculate_value(formula=self.load_external_data_formula)

            if self.load_external_data:
                if self.external_data_formula is None:
                    raise ComponentException("Cannot load external data - '{}' tag with '{}' attribute was not specified".
                                             format(self.externalDataTag, self.calculateTag), self.name)
                self.external_data = self.calculate_value(formula=self.external_data_formula)
                if not isinstance(self.external_data, bytes) and not isinstance(self.external_data, bytearray):
                        raise ComponentException("{} must result in a 'bytearray' or 'bytes', but is: {}".
                                             format(self.externalDataTag, type(self.external_data).__name__), self.name)
                # ensure that external data fills all space of this component
                if len(self.external_data) != self.size:
                    raise ComponentException("Invalid size of '{}', should be {} but is {}".
                                             format(self.externalDataTag, self.size, len(self.external_data)), self.name)

                # verify if loaded signature matches computed hash and given public key
                padding_args = SupportedPaddings.get_padding_args(self.salt_len, self.padding_scheme, self.sha_type)
                padding_class = SupportedPaddings.paddingClasses[self.padding_scheme]
                try:
                    public_key = self.key.key.rsa_key if self.key.key.key_type is RsaKeyType.Public else self.key.key.rsa_key.public_key()
                    public_key.verify(self.external_data,
                                      self.get_sha(),
                                      padding_class(*padding_args),
                                      utils.Prehashed(SupportedSHAs.shaClasses[self.sha_type]))
                except InvalidSignature as e:
                    raise ComponentException("Loaded signature does not match given key and computed hash".
                                             format(str(e)), self.name)
                print("Loaded signature is valid.\n")
            else:
                self.external_data = bytes([0xFF] * self.data_size)

            self._set_value(self.external_data[::-1] if self.reverse else self.external_data)
            return

        if self.signing_script:
            self._set_value(self.sign_external())
        else:
            padding_args = SupportedPaddings.get_padding_args(self.salt_len, self.padding_scheme, self.sha_type)
            padding_class = SupportedPaddings.paddingClasses[self.padding_scheme]

            if self.key.key.key_type is RsaKeyType.Public:
                raise ComponentException("Public key detected for signature", self.name)

            try:
                signature = self.key.sign(
                    self.get_sha(),
                    padding_class(*padding_args),
                    utils.Prehashed(SupportedSHAs.shaClasses[self.sha_type]))
            except (ValueError, TypeError) as e:
                raise ComponentException("Signing error: {}".format(e.args[0]), self.name)

            self._set_value(signature[::-1] if self.reverse else signature)
