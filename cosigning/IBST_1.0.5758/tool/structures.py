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
import copy
import sys
from os import urandom
from mmap import mmap
from enum import Enum
from cryptography.hazmat.primitives.asymmetric import padding, utils
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey, ECDSA
from cryptography.exceptions import InvalidSignature

from .ColorPrint import log
from .LibConfig import LibConfig
from .LibException import LibException, InternalBufferTooSmallException, ComponentException


class SupportedSHAs:
    class ShaType(Enum):
        SHA256 = "256"
        SHA384 = "384"
        SHA512 = "512"

    _supportedSHAClasses = {ShaType.SHA384: hashes.SHA384(), ShaType.SHA512: hashes.SHA512()}
    _legacySHAClasses = {ShaType.SHA256: hashes.SHA256()}

    _mask = 0xF000
    _maskVersions = {ShaType.SHA256: 0, ShaType.SHA384: 0x1000, ShaType.SHA512: 0x2000, }

    @classmethod
    def get_sha_type(cls, sha: str):  # pylint: disable=inconsistent-return-statements
        for sha_type in SupportedSHAs.ShaType:
            if sha_type.name.lower() == sha.lower():
                return sha_type
        cls.raise_not_supported(sha)

    @classmethod
    def get_sha_type_from_header(cls, header: int) -> ShaType:
        sha_value = header & cls._mask
        for sha, value in cls._maskVersions.items():
            if sha_value == value:
                return sha
        raise LibException(f"No sha type for given header: '{hex(header)}'.")

    @classmethod
    def get_sha_class(cls, sha_type: ShaType, is_legacy=False):
        if sha_type in SupportedSHAs._supportedSHAClasses:
            return cls._supportedSHAClasses[sha_type]
        if is_legacy and sha_type in cls._legacySHAClasses:
            return cls._legacySHAClasses[sha_type]
        LibConfig.exitCode = -1
        raise LibException(f"Given sha size is deprecated: {sha_type.value}.\n"
                           f"Accepted are: " + ", ".join([sha.value for sha in cls._supportedSHAClasses]))

    @classmethod
    def get_mask_version(cls, sha_type: ShaType):  # pylint: disable=inconsistent-return-statements
        if sha_type in cls._maskVersions:
            return cls._maskVersions[sha_type]
        cls.raise_not_supported(sha_type)

    @classmethod
    def raise_not_supported(cls, sha):
        raise LibException(f"Given sha type: {str(sha)} is not supported. "
                           f"Possible are: {', '.join([sha.name for sha in cls.ShaType])}")


class SupportedPaddings:
    class PaddingSchemeType(Enum):
        PKCS1_V1_5 = "v1_5"
        PKCS1_PSS = "PSS"

    _supportedPaddingClasses = {PaddingSchemeType.PKCS1_PSS: padding.PSS}
    _legacyPaddingClasses = {PaddingSchemeType.PKCS1_V1_5: padding.PKCS1v15}
    _mask = 0xF0000
    _maskVersions = {PaddingSchemeType.PKCS1_V1_5: 0x10000, PaddingSchemeType.PKCS1_PSS: 0x20000}
    maxSaltLen = padding.PSS.MAX_LENGTH

    @classmethod
    def get_padding_class(cls, padding_type: PaddingSchemeType, is_legacy=False):
        if padding_type in cls._supportedPaddingClasses:
            return cls._supportedPaddingClasses[padding_type]
        if is_legacy and padding_type in cls._legacyPaddingClasses:
            return cls._legacyPaddingClasses[padding_type]
        raise LibException(f"Given padding type is deprecated: {padding_type.value}.\n"
                           f"Accepted are: " + ", ".join([sha.value for sha in cls._supportedPaddingClasses]))

    @classmethod
    def get_padding_scheme_type_from_header(cls, header: int) -> PaddingSchemeType:
        padding_value = header & cls._mask
        for padding_type, value in cls._maskVersions.items():
            if padding_value == value:
                return padding_type
        raise LibException(f"No padding scheme type for given header: '{hex(header)}'.")

    @classmethod
    def get_padding_args(cls, padding_type, sha_type, is_legacy, salt_len=padding.PSS.AUTO):
        """
            Returns padding args needed for padding class with given padding type and sha type.
            :param padding_type: type of the padding (PSS, PKCS)
            :param sha_type: type of sha (256, 384, 514)
            :param is_legacy: tells if it is a legacy algorithm
            :param salt_len: recommended salt length, it won't affect the verification if left as PSS.AUTO
        """
        padding_args = {cls.PaddingSchemeType.PKCS1_V1_5: [], cls.PaddingSchemeType.PKCS1_PSS: [
            padding.MGF1(SupportedSHAs.get_sha_class(sha_type, is_legacy)), salt_len]}
        return padding_args[padding_type]

    @classmethod
    def get_mask_version(cls, padding_type: PaddingSchemeType):  # pylint: disable=inconsistent-return-statements
        if padding_type in cls._maskVersions:
            return cls._maskVersions[padding_type]
        cls.raise_not_supported(padding_type)

    @classmethod
    def raise_not_supported(cls, unsupported_padding):
        raise LibException(f"Given padding type: {str(unsupported_padding)} is not supported. "
                           f"Possible are: {', '.join([padd.name for padd in cls.PaddingSchemeType])}")


class AsymmetricKeyType(Enum):
    PUBLIC = "Public"
    PRIVATE = "Private"


class ByteOrder(Enum):
    LITTLE = 'little'
    BIG = 'big'


class RsaSigningKey:
    class RsaKeyLength(Enum):
        LEN2K = 256
        LEN3K = 384

    supported_rsa_mapping = [RsaKeyLength.LEN3K]
    legacy_rsa_mapping = [RsaKeyLength.LEN2K]

    ExponentSize = 4

    def __init__(self):
        (self.modulus, self.public_exponent, self.private_exponent, self.prime_p, self.prime_q, self._rsa_key,
         self.hashed_key) = [0] * 7
        self.key_type = AsymmetricKeyType.PUBLIC

    @property
    def rsa_key(self):
        return self._rsa_key

    @rsa_key.setter
    def rsa_key(self, value):
        self._rsa_key = value
        if isinstance(value, RSAPrivateKey):
            self.key_type = AsymmetricKeyType.PRIVATE
        else:
            self.key_type = AsymmetricKeyType.PUBLIC

    def sign(self, computed_hash, padding_algorithm, hash_algorithm, reverse: bool):
        signature = self.rsa_key.sign(computed_hash, padding_algorithm, hash_algorithm)
        return signature[::-1] if reverse else signature

    def verify(self, signature, computed_hash, padding_algorithm, hash_algorithm, _):
        """
            This method will verify a signature generated using a RSA key. In case the signature is using a
            non-recommended padding value the method will fallback to verification of the signature using PSS.auto.
            For more information refer to
            https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/?highlight=pss.auto#cryptography.hazmat.primitives.asymmetric.padding.PSS.AUTO
            :param signature: signature to be verified
            :param computed_hash: computed hash of signed data
            :param padding_algorithm: padding algorithm class, can be PSS or PKCS
            :param hash_algorithm: prehashed hash algorithm class, can be SHA256, SHA384 OR SHA512
        """
        if self.key_type == AsymmetricKeyType.PRIVATE:
            key = self.rsa_key.public_key()
        else:
            key = self.rsa_key
        padding_algorithm_auto = copy.deepcopy(padding_algorithm)
        padding_algorithm_auto._salt_length = padding.PSS.AUTO
        try:
            key.verify(bytes(signature), computed_hash, padding_algorithm, hash_algorithm)
        except InvalidSignature:
            pass
        else:
            return
        try:
            key.verify(bytes(signature), computed_hash, padding_algorithm_auto, hash_algorithm)
        except InvalidSignature as e:
            raise ComponentException("Loaded signature does not match given key and computed hash.") from e
        log().warning("Non-recommended salt length detected in the signature\n"
                      "Recommended value: " + str(padding_algorithm._salt_length))

    def formatted_key_type(self):
        return str(int(self.rsa_key.key_size / 1024)) + "K"


class EcSigningKey:
    class EcCurve(Enum):
        SECP256 = 'secp256r1'
        SECP384 = 'secp384r1'
        BRAINPOOL384 = 'brainpoolP384r1'
        INVALID = 'none'

    supported_curves = [EcCurve.BRAINPOOL384, EcCurve.SECP384]
    legacy_curves = [EcCurve.SECP256]
    _key_type_mask = 0xF0000
    _maskVersion = 0x30000
    _curve_mask = 0xF00
    _maskCurveVersions = {EcCurve.SECP256: 0, EcCurve.SECP384: 0x100, EcCurve.BRAINPOOL384: 0x200}

    def __init__(self):
        (self._curve, self.qx, self.qy, self._ec_key, self.coordinate_size, self.hashed_key, self.signature_r,
         self.signature_s) = [0] * 8
        self.key_type = AsymmetricKeyType.PUBLIC

    @property
    def curve(self):
        return self._curve

    @curve.setter
    def curve(self, value):
        curve_type = self.get_curve_type(value)
        self._curve = curve_type.value

    @property
    def ec_key(self) -> EllipticCurvePrivateKey:
        return self._ec_key

    @ec_key.setter
    def ec_key(self, value):
        self._ec_key: EllipticCurvePrivateKey = value
        if isinstance(value, EllipticCurvePrivateKey):
            self.key_type = AsymmetricKeyType.PRIVATE
        else:
            self.key_type = AsymmetricKeyType.PUBLIC

    def sign(self, computed_hash, length, hash_algorithm, reverse: bool):
        reverse_order = ByteOrder.LITTLE if reverse else ByteOrder.BIG
        # the same output here as openssl so called encoded
        signature = self.ec_key.sign(computed_hash, ECDSA(hash_algorithm))

        # from here, we are omitting header - just padded RS
        bytes_length = length if length and length > self.coordinate_size else self.coordinate_size
        return EcSigningKey.add_padding(signature, self.coordinate_size, bytes_length, reverse_order)

    def verify(self, signature, computed_hash, ecc_padding: int, hash_algorithm, reverse_order: int):
        """
        Verifies whether given signature is valid. Given signature can be in 2 formats:
            - encoded: ASN.1 DER format
            - decoded: r_component + ecc_padding + s_component + ecc_padding
                note: in decoded format, bytes can be without padding
        """
        if self.key_type == AsymmetricKeyType.PRIVATE:
            key = self.ec_key.public_key()
        else:
            key = self.ec_key
        try:
            # always try to decode to ASN.1 DER format - which cryptography accepts to be verified
            parsed_signature = self.convert_to_der_format(signature, self.coordinate_size, ecc_padding, reverse_order)
            key.verify(bytes(parsed_signature), computed_hash, ECDSA(hash_algorithm))
        except InvalidSignature as e:
            raise ComponentException('Loaded signature does not match given key and computed hash.') from e

    def formatted_key_type(self):
        return self.get_curve_type(self._curve).name

    @classmethod
    def add_padding(cls, signature: bytes, coordinate_size: int, bytes_length: int, reverse_order: ByteOrder):
        r, s = utils.decode_dss_signature(signature)
        r_bytes = r.to_bytes(coordinate_size, reverse_order.value)
        s_bytes = s.to_bytes(coordinate_size, reverse_order.value)
        r_padded = r_bytes + b'\0' * (bytes_length - coordinate_size)
        s_padded = s_bytes + b'\0' * (bytes_length - coordinate_size)

        return r_padded + s_padded

    @classmethod
    def convert_to_padded_format(cls, signature: bytes, coordinate_size: int, ecc_padding: int, reverse_order: int):
        """
        Converts given signature to RAW format with padding which is:
          r_component + ecc_padding + s_component + ecc_padding
        Note: If given signature is not in DER format, then validate limits and convert it.
        """
        if not EcSigningKey.is_der_format(signature):
            EcSigningKey.validate_signature_limits(len(signature), ecc_padding, coordinate_size)
            converted_signature = EcSigningKey.convert_to_der_format(signature, coordinate_size, ecc_padding,
                                                                     reverse_order)
        else:
            converted_signature = signature

        bytes_length = ecc_padding if ecc_padding and ecc_padding > coordinate_size else coordinate_size
        byte_order = ByteOrder.LITTLE if reverse_order else ByteOrder.BIG
        return EcSigningKey.add_padding(converted_signature, coordinate_size, bytes_length, byte_order)

    @classmethod
    def convert_to_der_format(cls, signature: bytes, coordinate_size: int, ecc_padding: int, reverse_order: int):
        """
        Converts given signature to ASN.1 DER format without padding which is a openssl output for command:
        openssl pkeyutl -sign -inkey key.pem -keyform PEM -in hash.bin -pkeyopt digest:sha256 > encoded_signature.bin
        """

        if EcSigningKey.is_der_format(signature):
            return signature

        # ecc_padding is 2 times as the RAW format of signature is as below:
        # r_component + ecc_padding + s_component + ecc_padding
        max_padded_size = 2 * ecc_padding
        max_coordinate_size = 2 * coordinate_size
        signature_length = len(signature)
        order_str = ByteOrder.LITTLE.value if reverse_order else ByteOrder.BIG.value

        r = signature[:coordinate_size]
        if signature_length < max_padded_size:
            s = signature[coordinate_size:max_coordinate_size]
        else:
            s = signature[ecc_padding:ecc_padding + coordinate_size]

        return utils.encode_dss_signature(int.from_bytes(r, order_str), int.from_bytes(s, order_str))

    @classmethod
    def is_der_format(cls, signature):
        """
        Checks whether given signature is in ASN.1 DER format
        """
        try:
            # if possible to get r & s, then the given signature is already in ASN.1 DER format
            utils.decode_dss_signature(signature)
            return True
        except ValueError:
            return False

    @classmethod
    def validate_signature_limits(cls, signature_length: int, ecc_padding: int, coordinate_size: int):
        """
        Checks whether given signature length is:
        - not greater then the max padded length
        - not lower then the min length of both RS components
        Note: If tested signature is in ASN.1 DER format,
              length of that signature will be between max coordinate size and max padded size.
        """
        max_padded_size = ecc_padding * 2
        max_coordinate_size = coordinate_size * 2
        if signature_length > max_padded_size:
            raise LibException(
                f"Given signature length '{signature_length}' greater then the max padded length '{max_padded_size}'")
        if signature_length < max_coordinate_size:
            raise LibException(
                f"Given signature length '{signature_length}' lower then the minimum length of RS components '"
                f"{max_coordinate_size}'")

    @classmethod
    def is_ec_header(cls, header: int):
        return header & cls._key_type_mask == cls._maskVersion

    @classmethod
    def get_curve_type(cls, curve: str):
        for en_curve in cls.EcCurve:
            if en_curve.value.lower() == curve.lower():
                return en_curve
        return cls.EcCurve.INVALID

    @classmethod
    def get_curve_type_from_header(cls, header: int):
        curve_value = header & cls._curve_mask
        for curve, value in cls._maskCurveVersions.items():
            if curve_value == value:
                return curve
        raise LibException(f"No ec curve type for given header: '{hex(header)}'.")

    @classmethod
    def get_mask_version(cls, curve_type: EcCurve):
        if curve_type in cls._maskCurveVersions:
            return cls._maskVersion + cls._maskCurveVersions[curve_type]
        invalid_mask = 0
        return invalid_mask


class DataNode:
    class Tags:
        NAME = "name"
        VALUE = "value"
        PATH = "path"
        START = "start"
        END = "end"
        START_INDEX = "start_index"
        END_INDEX = "end_index"
        EXCLUDE_RANGES = "exclude_ranges"

    name = None
    value = None
    path = None
    start = None
    end = None
    start_index = None
    end_index = None

    def __init__(self, xml_node):
        if self.Tags.NAME in xml_node.attrib:
            self.name = xml_node.attrib[self.Tags.NAME]
        if self.Tags.VALUE in xml_node.attrib:
            self.value = xml_node.attrib[self.Tags.VALUE]
        if self.Tags.PATH in xml_node.attrib:
            self.path = xml_node.attrib[self.Tags.PATH]
        if self.Tags.START in xml_node.attrib:
            self.start = xml_node.attrib[self.Tags.START]
        if self.Tags.END in xml_node.attrib:
            self.end = xml_node.attrib[self.Tags.END]
        if self.Tags.START_INDEX in xml_node.attrib:
            self.start_index = xml_node.attrib[self.Tags.START_INDEX]
        if self.Tags.END_INDEX in xml_node.attrib:
            self.end_index = xml_node.attrib[self.Tags.END_INDEX]
        if self.Tags.EXCLUDE_RANGES in xml_node.attrib:
            self.exclude_ranges = xml_node.attrib[self.Tags.EXCLUDE_RANGES]
        else:
            self.exclude_ranges = None

        if not self.value and not self.path and (not self.start or not self.end):
            raise LibException(
                    f"Missing mandatory attributes '{self.Tags.VALUE}' or '{self.Tags.PATH}' or '{self.Tags.START}' "
                    f"and '{self.Tags.END}'.")

    def check_start_end(self):
        if not self.start or not self.end:
            raise LibException(f"Missing mandatory attributes '{self.Tags.START}' and '{self.Tags.END}'.")

    def check_name(self):
        if not self.name:
            raise LibException(f"Missing mandatory attributes '{self.Tags.NAME}'.")


class AesEncryption:
    class KeyLength(Enum):
        AES128 = 128
        AES256 = 256

    class Mode(Enum):
        CBC = 'CBC'
        CTR = 'CTR'

    modeTypes = {Mode.CBC: 1, Mode.CTR: 2}
    aesBlockSizeBytes = algorithms.AES.block_size // 8

    _paddingTypes = None
    _supportedAesSizes = [KeyLength.AES256]
    _legacyAesSizes = [KeyLength.AES128]

    @classmethod
    def get_padding_types(cls):
        if cls._paddingTypes is None:
            cls._paddingTypes = {cls.Mode.CBC: cls.ErrorPadding, cls.Mode.CTR: cls.NoPadding}
        return cls._paddingTypes

    @classmethod
    def parse_mode(cls, mode_str):
        try:
            return cls.Mode(mode_str.upper())
        except Exception as e:
            values = [item.value for item in cls.Mode]
            raise LibException(f"Invalid name of encryption mode, choose one of: {', '.join(values)}.") from e


    @classmethod
    def get_mode_instance(cls, name, iv=None):
        """
        Gets new mode instance.
        When starting new encryption, a new initialization vector
        of random data must be generated. Old one should not be reused.
        """
        if name == cls.Mode.CBC:
            return modes.CBC(iv if iv is not None else urandom(cls.aesBlockSizeBytes))
        if name == cls.Mode.CTR:
            return modes.CTR(iv if iv is not None else urandom(cls.aesBlockSizeBytes))
        raise LibException(f"There is no such encryption mode: {name}")

    @classmethod
    def create_initialisation_vector(cls):
        return urandom(cls.aesBlockSizeBytes)

    @classmethod
    def get_empty_initialisation_vector(cls):
        return bytes([0] * cls.aesBlockSizeBytes)

    @classmethod
    def get_key_length_type(cls, key_length: int, is_legacy):  # pylint: disable=inconsistent-return-statements
        results = list(filter(lambda key: key.value == key_length, cls._supportedAesSizes))
        if not results and is_legacy:
            results = list(filter(lambda key: key.value == key_length, cls._legacyAesSizes))
        if results:
            return next(iter(results))
        cls._raise_not_supported(key_length, is_legacy)

    @classmethod
    def _raise_not_supported(cls, key_len, is_legacy):
        size_collection = cls._supportedAesSizes if is_legacy else cls._legacyAesSizes + cls._supportedAesSizes
        raise LibException(f"Given key size: {str(key_len)} is not supported.\n"
                           f"Possible are: {', '.join([str(en_k.value) for en_k in size_collection])}.")

    @classmethod
    def get_padding_instance(cls, encryption_mode):
        # pylint: disable=unsupported-membership-test,unsubscriptable-object
        if encryption_mode not in cls.get_padding_types():
            raise LibException(f"There is no padding type defined for following encryption mode: {encryption_mode}.")
        return cls.get_padding_types()[encryption_mode]()
        # pylint: enable=unsupported-membership-test,unsubscriptable-object

    class Padding:
        def get_encrypted_data_size(self, data_size):
            raise LibException("Invalid padding - base class used")

        @staticmethod
        def calculate_padding_length( data_size):
            return -data_size % AesEncryption.aesBlockSizeBytes

        def preencrypt(self, data):
            raise LibException("Invalid padding - base class used")

        def postencrypt(self, data):
            raise LibException("Invalid padding - base class used")

    class NoPadding(Padding):
        # For CTR mode we don't need any padding
        def get_encrypted_data_size(self, data_size):
            return data_size

        def preencrypt(self, data):
            return data

        def postencrypt(self, data):
            return data

    class ErrorPadding(Padding):
        # This class doesn't allow any padding - data must be of proper size, otherwise an error is raised
        def get_encrypted_data_size(self, data_size):
            padding_length = self.calculate_padding_length(data_size)
            if padding_length:
                raise LibException(
                        f"Padding is disabled for this encryption mode, data must be aligned to "
                        f"{AesEncryption.aesBlockSizeBytes}. Use 'padding' attribute to align data size.")
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
        except OverflowError as e:
            offset = args[0]
            raise LibException(f"Value of {hex(offset)} is too big. Limit is {hex(sys.maxsize)}") from e
        except ValueError as e:
            if self._error_message_pattern in str(e):
                raise InternalBufferTooSmallException(self.max_size) from e
            raise

    def write(self, *args, **kwargs):
        try:
            return super().write(*args, **kwargs)
        except ValueError as e:
            if self._error_message_pattern in str(e):
                raise InternalBufferTooSmallException(self.max_size) from e
            raise

    def reduce_buffer_to_match_content(self):
        current_offset = self.tell()
        if current_offset == 0:
            # We cannot create mmap with size 0 so we set size to 1
            # but the current position (tell()) will stay at 0 so it will be fine
            new_buffer = Buffer(self._file_no, 1)
            new_buffer._max_size = 0  # pylint: disable=protected-access
        else:
            self.seek(0)
            content = self.read(current_offset)
            new_buffer = Buffer(self._file_no, current_offset)
            new_buffer.write(content)
        self.flush()
        self.close()
        return new_buffer


class ValueWrapper:
    class Tags:
        VALUE = 'value'
        CALCULATE = 'calculate'

    def __init__(self, xml_node, component, convert_function=None):
        self._value = None
        self._formula = None
        self.component = component
        if self.Tags.VALUE in xml_node.attrib:
            self._value = xml_node.attrib[self.Tags.VALUE]
            # if convert_function has been given then we use it to convert convent of 'value' attribute
            if convert_function:
                self._value = convert_function(self._value)
        if self.Tags.CALCULATE in xml_node.attrib:
            self._formula = xml_node.attrib[self.Tags.CALCULATE]

    def needs_calculation(self):
        return self._value is None and self._formula is not None

    @property
    def value(self):
        if self.needs_calculation():
            self._value = self.component.calculate_value(self._formula)
        return self._value

    def recalculate(self):
        if self._formula is not None:
            self._value = self.component.calculate_value(self._formula)
        return self._value
