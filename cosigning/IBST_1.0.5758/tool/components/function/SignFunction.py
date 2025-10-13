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

import subprocess  # nosec
import os

from enum import Enum
from cryptography.hazmat.primitives.asymmetric import utils

from ...FileManager import FileManager
from ...FileOpener import open_file
from ...LibException import ComponentException, LibException
from .HashFunction import HashFunction
from ...structures import SupportedSHAs, SupportedPaddings, RsaSigningKey, EcSigningKey
from ...Converter import Converter
from ...ColorPrint import log
from ...LibConfig import LibConfig


class SignFunction(HashFunction):
    # pylint: disable=line-too-long
    """Extension of 'hash_function' used to hash given input data and sign the hash with given key.
     Here's a list of supported key algorithms:

    Supported algorithm             Notes
    -------------------             -----
    RSA-2048                        Legacy mode only
    RSA-3072
    RSA-4096
    ECC-256 secp256r1 curve         Legacy mode only
    ECC-384 secp384r1 curve
    ECC-384 brainpoolP384r1 curve
    AES-128                         Legacy mode only
    AES-256

    Sign function inherits all configurable children and attributes from hash function,
    but there are few new signing-related options to configure:

    Configurable children   Required    Description
    ---------------------   --------    -----------
    key                     yes         Points to the key used for signing
    padding_scheme          no          Applies only for RSA keys, indicates what padding scheme should be used (possible values are 'PSS' for PSS and 'v1_5' for PKCSv1_5, default is PKCSv1_5), optional salt_len argument can be provided to indicate salt length to be used for signature creation
    signing_utility         no          Path to the external signing script, not used if set to empty string (for more information about external signing refer to **External signing tool section in IBST user guide**)
    signing_utility_timeout no          Sets the timeout for external signing script
    load_external_data      no          Indicates if the signature should be loaded from external file instead of being calculated
    external_data           no          External signature data (for example, can be extracted from file component by using *data* property)
    offline_signing         no          If set to 1, the signature will not be calculated and instead only the hash will be saved so the user can sign it using external method and run IBST again with load_external_data set to 1 and external_data provided (for more information about offline signing refer to **Offline signing section in IBST user guide**)

    Here's an example:

    ```xml
    <function_sign name="signature" legacy="false">
        <key value="/settings/key" />
        <sha value="512" />
        <padding_scheme value="'PSS'" salt_len="64"/>
        <input>
            <data path="/settings/input_file" />
        </input>
        <save_hash calculate="/settings/output_hash_path.empty == False
                              and /settings/save_hash.value == 1" />
        <save_hash_path calculate="/settings/output_hash_path.path" />
        <load_external_data calculate="/settings/signature_file.size > 0" />
        <external_data calculate="/settings/signature_file.data" />
        <offline_signing calculate="/settings/offline_signing.value" />
        <signing_utility calculate="/settings/signing_utility"/>
    </function_sign>
    ```
    """
    # pylint: enable=line-too-long

    class Tags(HashFunction.Tags):
        KEY = "key"
        PADDING_SCHEME = "padding_scheme"
        PADDING_SALT_LEN = "salt_len"
        SIGNING_UTILITY = "signing_utility"
        SIGNING_UTILITY_TIMEOUT = "signing_utility_timeout"
        LOAD_EXTERNAL_DATA = "load_external_data"
        EXTERNAL_DATA = "external_data"
        OFFLINE_SIGNING = "offline_signing"
        ECC_PADDING = "ecc_padding"
        SIGNATURE_FILE = "signature_file"
        SIGNATURE_PLACEHOLDER = 'signature_placeholder'
        COMPONENT_NAME = 'component_name'

    key_path = None
    key = None
    padding_scheme = SupportedPaddings.PaddingSchemeType.PKCS1_V1_5
    padding_scheme_formula = None
    signing_script_path = None
    signing_script = None
    signing_script_timeout_formula = None
    signing_script_timeout = 60
    salt_len = SupportedPaddings.maxSaltLen
    load_external_data_formula = None
    load_external_data = False
    external_data_formula = None
    external_data = None
    offline_signing_formula = None
    offline_signing = False
    ecc_padding = None

    class ComponentProperty(Enum):
        HEADER_VERSION = "header_version"
        VALUE = "value"
        SIZE = "size"

    @HashFunction.size.getter  # pylint: disable=no-member
    def size(self):
        return self._size

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        self._parse_key_tag(xml_node)
        self._parse_padding_scheme_tag(xml_node)
        self._parse_signing_utility_tag(xml_node)
        self.load_external_data_formula = self.parse_extra_node(xml_node, self.Tags.LOAD_EXTERNAL_DATA)
        self.external_data_formula = self.parse_extra_node(xml_node, self.Tags.EXTERNAL_DATA)
        self.offline_signing_formula = self.parse_extra_node(xml_node, self.Tags.OFFLINE_SIGNING)
        ecc_padding_str = self.parse_extra_node(xml_node, self.Tags.ECC_PADDING, self.Tags.VALUE)
        if ecc_padding_str:
            self.ecc_padding = Converter.string_to_int(ecc_padding_str)
        self._try_parse_signature_file_tag(xml_node)
        self.signature_placeholder = self._parse_signature_placeholder_tag(
            xml_node) if self.calc_only else None
        self.component_name = self._parse_component_name(xml_node)

    def _parse_component_name(self, xml_node):
        value = self.parse_extra_node(xml_node, self.Tags.COMPONENT_NAME, self.Tags.VALUE)
        if self.offline_signing_formula:
            self.offline_signing = self.calculate_value(formula=self.offline_signing_formula)

        # Component name node is not expected during offline signing on IBST tool.
        if not value and self.offline_signing and LibConfig.toolType != LibConfig.ToolType.IBST:
            raise ComponentException(f"'{self.name}' node is missing child node: '{self.Tags.COMPONENT_NAME}'",
                                     self.name)
        if not value:
            return None

        index_marker = ' [index]'
        marker_exists = index_marker in value
        index_value = self.get_table_index()
        if marker_exists and index_value is not None:
            return value.replace(index_marker, f" [{str(index_value)}]")
        return value if not marker_exists else value.replace(index_marker, '')

    def _parse_signature_placeholder_tag(self, xml_node):
        signature_placeholder_node = self._parse_node(xml_node, self.Tags.SIGNATURE_PLACEHOLDER)

        return self.calculate_value(signature_placeholder_node.attrib[self.Tags.CALCULATE])

    def _try_parse_signature_file_tag(self, xml_node):
        try:
            signature_file_node = self._parse_node(xml_node, self.Tags.SIGNATURE_FILE)
        except ComponentException:
            # offline signing will be unsupported - IBST config files
            return

        self.signature_file_formula = signature_file_node.attrib[self.Tags.CALCULATE]
        if self._skip_calculates:
            self.signature_file = None
        else:
            self.signature_file = self.calculate_value(self.signature_file_formula)

    def _parse_key_tag(self, xml_node):
        key_node = self._parse_node(xml_node, self.Tags.KEY)

        self.key_path = key_node.attrib[self.Tags.VALUE]
        self.validate_formula = self._parse_attribute(key_node, self.Tags.VALIDATE_FORMULA, False, None)
        if not self.validate_formula:
            return

        key = self.calculate_value(self.key_path, allow_calculate=True)

        if not key or not key.value:
            return

        self.check_validate_formula()

    def check_validate_formula(self):
        if self.validate_formula:
            if not self.calculate_value(self.validate_formula, True):
                raise ComponentException("Unsupported key length", self.name)

    def _parse_padding_scheme_tag(self, xml_node):
        padding_scheme_node = xml_node.find(self.Tags.PADDING_SCHEME)
        if padding_scheme_node is not None:
            self.padding_scheme_formula = padding_scheme_node.attrib[self.Tags.VALUE]
            allowed_padding_schemes = [e.value for e in SupportedPaddings.PaddingSchemeType]
            if self.padding_scheme_formula in allowed_padding_schemes:
                padding_scheme_value = self.padding_scheme_formula
            else:
                calculate_exception = None
                try:
                    padding_scheme_value = self.calculate_value(self.padding_scheme_formula, allow_calculate=True)
                except ComponentException as ex:
                    calculate_exception = ex
                if calculate_exception or padding_scheme_value not in allowed_padding_schemes:
                    raise ComponentException(f"Invalid value for '{self.Tags.PADDING_SCHEME}', use one of: "
                                             f"'{', '.join(allowed_padding_schemes)}'"
                                             f"{', ' + str(calculate_exception) if calculate_exception else ''}",
                                             self.name)
            self.padding_scheme = SupportedPaddings.PaddingSchemeType(padding_scheme_value)
            if self.Tags.PADDING_SALT_LEN not in padding_scheme_node.attrib or \
                    (self.Tags.PADDING_SALT_LEN in padding_scheme_node.attrib and
                     not padding_scheme_node.attrib[self.Tags.PADDING_SALT_LEN]):
                self.salt_len = self._calculate_salt_length()
            else:
                try:
                    self.salt_len = self.calculate_value(padding_scheme_node.attrib[self.Tags.PADDING_SALT_LEN],
                                                         allow_calculate=True)
                except (ValueError, TypeError, ComponentException) as e:
                    raise ComponentException(
                            f"Incorrect salt_len: {padding_scheme_node.attrib[self.Tags.PADDING_SALT_LEN]}",
                            self.name) from e

    def _parse_signing_utility_tag(self, xml_node):
        signing_util_node = xml_node.find(self.Tags.SIGNING_UTILITY)
        if signing_util_node is not None:
            if self.Tags.VALUE in signing_util_node.attrib:
                self.signing_script = signing_util_node.attrib[self.Tags.VALUE]
            else:
                self.signing_script_path = signing_util_node.attrib[self.Tags.CALCULATE]

        signing_util_timeout_node = xml_node.find(self.Tags.SIGNING_UTILITY_TIMEOUT)
        if signing_util_timeout_node is not None:
            if self.Tags.CALCULATE not in signing_util_timeout_node.attrib:
                raise ComponentException(f"Missing mandatory attribute '{self.Tags.SIGNING_UTILITY_TIMEOUT}' "
                                         f"in '{self.Tags.SIGNING_UTILITY}'", self.name)
            timeout_formula = signing_util_timeout_node.attrib[self.Tags.CALCULATE]
            if timeout_formula:
                self.signing_script_timeout_formula = timeout_formula

    def _get_property(self, component_property, _=False, report_usage=False):
        if component_property == SignFunction.ComponentProperty.HEADER_VERSION:
            return self.create_header_version()
        if component_property == self.ComponentProperty.SIZE:
            return self.size
        return super()._get_property(component_property, _, report_usage)

    def create_header_version(self):
        if isinstance(self.key.key, RsaSigningKey):
            version = SupportedPaddings.get_mask_version(self.padding_scheme)
        else:
            curve_type = EcSigningKey.get_curve_type(self.key.key.curve)
            version = EcSigningKey.get_mask_version(curve_type)
        version += SupportedSHAs.get_mask_version(self.sha_type)
        return version

    def sign_external(self, buffer=None):
        data_file_name = 'data_to_sign.bin'
        signature_file_name = 'signature.bin'
        sha_arg = "sha" + self.sha_type.value

        FileManager.save_binary_file(data_file_name, self.get_input_bytes(buffer))

        abs_in = os.path.abspath(data_file_name)
        abs_path = os.path.dirname(abs_in)
        abs_out = os.path.join(abs_path, signature_file_name)

        if not os.path.isabs(self.signing_script):
            raise ComponentException(f"Full path must be used for {self.Tags.SIGNING_UTILITY}", self.name)

        cmd = ['python', self.signing_script, sha_arg, self.key.value, abs_out, abs_in, self.padding_scheme.value]

        try:
            log().info(f'Calling external signing script: "{" ".join(cmd)}"')
            log().warning('WARNING:\nMake sure that the called script can be safely called and '
                          'does not pose any threat!')
            subprocess.check_call(cmd, shell=False, timeout=self.signing_script_timeout)  # nosec
        except subprocess.CalledProcessError as e:
            raise ComponentException(
                f"Problem calling signing script '{self.signing_script}': {e.returncode}", self.name) from e
        except subprocess.TimeoutExpired as e:
            raise ComponentException(
                f"Timeout ({self.signing_script_timeout}) occurred while calling signing script "
                f"'{self.signing_script}'", self.name) from e

        try:
            with open_file(signature_file_name, 'rb') as file:
                signature = file.read()
        except FileNotFoundError as ex:
            raise ComponentException(f"Cannot open calculated signature. {ex.strerror}: {ex.filename}", self.name) \
                from ex

        return signature[::-1]

    def _build_layout(self):
        self.key = self.calculate_value(self.key_path, allow_calculate=True)
        self._size = self._calc_size()
        self._validate_key()
        self.set_value(b'\0' * self.size)
        if self.signing_script_path:
            self.signing_script = self.calculate_value_from_path(self.signing_script_path).value
        if self.signing_script_timeout_formula:
            timeout_str = self.calculate_value(self.signing_script_timeout_formula)
            if timeout_str:
                self.signing_script_timeout = Converter.string_to_int(timeout_str)
            else:
                self.signing_script_timeout = None

    def _calc_size(self):
        sign_size = self.key.get_property("signature_size")  # * 2 because we have Qx and Qy
        if isinstance(self.key.key, EcSigningKey) and self.ecc_padding and self.ecc_padding * 2 > sign_size:
            return self.ecc_padding * 2
        return sign_size

    def _validate_key(self):
        """
        Validate the keys used for signing against key type:
        Rsa Signing Key: Check key size and legacy attribute
            Legacy == True -> anything goes
            Legacy == False -> only Rsa 3k keys or longer
        Ec Signing Key: Check key curve and legacy attribute
            Key curve must be one of: 'secp256r1', 'secp384r1' or 'brainpoolP384r1'
        """
        if isinstance(self.key.key, RsaSigningKey):
            if self.key.key.rsa_key.key_size < (RsaSigningKey.RsaKeyLength.LEN3K.value * 8) and not self.is_legacy:
                possible_keys = self.get_valid_rsa_keys()
                raise LibException(f"Given signing key size: {self.key.key.rsa_key.key_size} is not supported. "
                                   f"Possible are: {', '.join([str(rsa.value * 8) for rsa in possible_keys])}")
        elif isinstance(self.key.key, EcSigningKey):
            curve_type_name = EcSigningKey.get_curve_type(self.key.key.curve)
            if self.key.key.curve == EcSigningKey.EcCurve.INVALID.value or \
                    (curve_type_name in EcSigningKey.legacy_curves and not self.is_legacy):
                possible_keys = self.get_valid_ec_keys()
                raise LibException(f"Given ec curve type: {self.key.key.ec_key.curve.name} is not supported. "
                                   f"Possible are: {', '.join([curve.value for curve in possible_keys])}")

    def get_valid_rsa_keys(self):
        """
        Get valid rsa keys against legacy attribute and signature block size.
        Signature placeholder is set according to calc_only parameter:
            calc_only == True -> get signature_placeholder from xml_node
            calc_only == False -> signature_placeholder = None
        Legacy == True:
            if signature block size is sufficient, valid keys are: legacy and supported
            else: only legacy keys
        Legacy == False -> only supported keys
        """
        signature_block_size = self.signature_placeholder.size if self.signature_placeholder else self.size
        if self.is_legacy:
            if self.is_legacy and signature_block_size >= self.key.key.rsa_key.key_size:
                return RsaSigningKey.legacy_rsa_mapping + RsaSigningKey.supported_rsa_mapping
            return RsaSigningKey.legacy_rsa_mapping
        return RsaSigningKey.supported_rsa_mapping

    def get_valid_ec_keys(self):
        """
        Get valid ec signing keys against legacy attribute and signature block size.
        Signature placeholder is set according to calc_only parameter:
            calc_only == True -> get signature_placeholder from xml_node
            calc_only == False -> signature_placeholder = None
        Legacy == True:
            if signature block size is sufficient, valid keys are: legacy and supported
            else: only legacy keys
        Legacy == False -> only supported keys
        """
        signature_block_size = self.signature_placeholder.size if self.signature_placeholder else self.size
        if self.is_legacy:
            if self.is_legacy and signature_block_size >= self.key.key.ec_key.key_size:
                return EcSigningKey.legacy_curves + EcSigningKey.supported_curves
            return EcSigningKey.legacy_curves
        return EcSigningKey.supported_curves

    def _build(self, buffer):
        super()._build(buffer)

        self._validate_key()

        if self.offline_signing_formula:
            self.offline_signing = self.calculate_value(formula=self.offline_signing_formula, build_process=True)

        if self.offline_signing:
            log().warning(f"{self.get_string_path()}:\nOffline signing - signature will NOT be computed!\n")

            if self.load_external_data_formula:
                self.load_external_data = self.calculate_value(formula=self.load_external_data_formula,
                                                               build_process=True)

            if self.load_external_data:
                if self.external_data_formula is None:
                    raise ComponentException(
                            f"Cannot load external data - '{self.Tags.EXTERNAL_DATA}' tag with '{self.Tags.CALCULATE}' "
                            f"attribute was not specified", self.name)
                self.external_data = self.calculate_value(formula=self.external_data_formula, build_process=True)
                if not isinstance(self.external_data, bytes) and not isinstance(self.external_data, bytearray):
                    raise ComponentException(
                        f"{self.Tags.EXTERNAL_DATA} must result in a 'bytearray' or 'bytes', but is: "
                        f"{type(self.external_data).__name__}", self.name)

                # convert to R+PADDING+S+PADDING
                if isinstance(self.key.key, EcSigningKey) and EcSigningKey.is_der_format(self.external_data):
                    self.external_data = EcSigningKey.convert_to_padded_format(self.external_data,
                                                                               self.key.key.coordinate_size,
                                                                               self.ecc_padding, self.reverse)
                # verify if loaded signature matches computed hash and given public key
                self.verify_signature()
            else:
                self.external_data = bytes([0xFF] * self.size)

            # convert to R+PADDING+S+PADDING
            if isinstance(self.key.key, EcSigningKey) and EcSigningKey.is_der_format(self.external_data):
                self.external_data = EcSigningKey.convert_to_padded_format(self.external_data,
                                                                           self.key.key.coordinate_size,
                                                                           self.ecc_padding, self.reverse)
            if isinstance(self.key.key, EcSigningKey):
                self.set_value(self.external_data)
            else:
                self.set_value(self.external_data[::-1] if self.reverse else self.external_data)
            return

        if self.signing_script:
            self.set_value(self.sign_external(buffer))
        else:
            if not self.key.is_private:
                raise ComponentException("Public key detected for signature", self.name)

            if isinstance(self.key.key, RsaSigningKey):
                padding_args = SupportedPaddings.get_padding_args(self.padding_scheme, self.sha_type,
                                                                  self.is_legacy, self.salt_len)
                padding_class = SupportedPaddings.get_padding_class(self.padding_scheme, self.is_legacy)
                padding = padding_class(*padding_args)
            else:
                padding = self.ecc_padding

            try:
                signature = self.key.sign(self.get_sha(buffer), padding,
                                          utils.Prehashed(SupportedSHAs.get_sha_class(self.sha_type, self.is_legacy)),
                                          self.reverse)
            except (ValueError, TypeError) as e:
                raise ComponentException(f"Signing error: {e.args[0]}", self.name) from None
            self.set_value(signature)

    def signature_not_given(self):
        return not self.signature_file or not self.signature_file.value

    def verify_signature(self):
        if isinstance(self.key.key, RsaSigningKey):
            padding_args = SupportedPaddings.get_padding_args(self.padding_scheme, self.sha_type,
                                                              self.is_legacy, self.salt_len)
            padding_class = SupportedPaddings.get_padding_class(self.padding_scheme, self.is_legacy)
            padding = padding_class(*padding_args)
            if len(self.external_data) != self.size:
                raise ComponentException(
                    f"Invalid size of '{self.Tags.EXTERNAL_DATA}', "
                    f"should be {self.size} but is {len(self.external_data)}", self.name)
            self.key.verify(self.external_data, self.sha, padding,
                            utils.Prehashed(SupportedSHAs.get_sha_class(self.sha_type, self.is_legacy)))
        else:
            if self.ecc_padding is None:
                self.ecc_padding = self.size // 2
            padding = self.ecc_padding
            EcSigningKey.validate_signature_limits(len(self.external_data), self.ecc_padding,
                                                   self.key.key.coordinate_size)
            self.key.verify(self.external_data, self.sha, padding,
                            utils.Prehashed(SupportedSHAs.get_sha_class(self.sha_type, self.is_legacy)), self.reverse)
        log().info(f"Loaded signature: {self.component_name} is valid.\n")
        return True

    def convert_to_padded_format(self, signature: bytes):
        if isinstance(self.key.key, EcSigningKey):
            return EcSigningKey.convert_to_padded_format(signature, self.key.key.coordinate_size, self.ecc_padding,
                                                         self.reverse)
        return signature

    def apply_signature(self, buffer, offset):
        buffer[offset:offset + self.size] = self.external_data[::-1] if self.reverse else self.external_data

    def _calculate_salt_length(self):
        available_salt_lengths = {SupportedSHAs.ShaType.SHA256: 32,
                                  SupportedSHAs.ShaType.SHA384: 48,
                                  SupportedSHAs.ShaType.SHA512: 64}
        return available_salt_lengths[self.sha_type]
