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
import operator
import os
import os.path
import mmap
import re
import json
from dataclasses import dataclass

from sys import maxsize
from enum import Enum
from functools import partial

import sys
import math

from datetime import datetime
from typing import Any, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, ec, utils
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from .FileManager import FileManager
from .FileOpener import open_file
from .LibException import LibException, ComponentException, JSONException, XmlAttrException, \
    FileDoesNotExistException, IncorrectFileTypeException, InvalidFilePathException
from . import structures as ss, ColorPrint
from .Converter import Converter
from .ColorPrint import log

bin_operators_map = {  # python operators precedence
    'or': (lambda a, b: a or b, False),
    'and': (lambda a, b: a and b, False),
    'not': (operator.not_, False),
    '!=': (operator.ne, False),
    '==': (operator.eq, False),
    '>': (operator.gt, False),
    '>=': (operator.ge, False),
    '<=': (operator.le, False),
    '<': (operator.lt, False),
    '^': (operator.xor, True),
    '|': (operator.or_, True),
    '&': (operator.and_, True),
    '<<': (operator.lshift, True),
    '>>': (operator.rshift, True),
    '+': (operator.add, True),
    '-': (operator.sub, True),
    '*': (operator.mul, True),
    '/': (operator.floordiv, True),
    '%': (operator.mod, True),
}
ILLEGAL_PATH_CHARACTERS = '[@!#$%^&*<>?|}{~:]'


def calc_operator(oper: str, left, right):
    return bin_operators_map[oper][0](left, right)


class ComponentProperty(Enum):
    COMPONENT = None
    BCD = 'bcd'
    CHILD_COUNT = "child_count"
    CHILD_COUNT_ENABLED = 'child_count_enabled'
    DATA = 'data'
    EMPTY = 'empty'
    ENABLED = 'enabled'
    END = 'end'
    MAX_ENTRY_COUNT = 'max_entry_count'
    OFFSET = 'offset'
    SIZE = 'size'
    VALUE = 'value'
    PATH = 'path'
    # Key / Signature specific attributes
    COORDINATE_SIZE = 'coordinate_size'
    HASHED_KEY = 'hashed_key'
    HEADER_VERSION = 'header_version'
    EXPONENT = 'exponent'
    MODULUS = 'modulus'
    SIGNATURE_SIZE = 'signature_size'
    TYPE_RSA = 'type_rsa'
    QX = 'qx'
    QY = 'qy'
    CURVE = 'curve'
    CURVE_MAGIC = 'curve_magic'


def calculate_hash(buffer, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    if hash_type:
        digest = hashes.Hash(ss.SupportedSHAs.get_sha_class(hash_type, is_legacy), backend=default_backend())
        digest.update(bytes(buffer))
        return digest.finalize()
    raise LibException("Hash type not supported")


def is_windows():
    """
    Checks whether current OS is Windows
    :return: True if current OS is Windows
    """
    return os.name == "nt"


def process_key_file(file_name, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
        msg = f'Could not open key file - "{file_name}"'
        raise LibException(msg)

    use_dbg_key = False

    with open_file(file_name, 'rb') as kfile:
        line = b'(8:sequence'
        buffer = kfile.read(len(line))
        if line == buffer:
            use_dbg_key = True

    if use_dbg_key:
        # convert the raw data into the right structure
        key = convert_rsa_key_format(file_name, hash_type, is_legacy)
    else:
        key = process_openssl_key(file_name, hash_type, is_legacy)

    if isinstance(key, ss.RsaSigningKey):
        expected_exponent = 0x010001
        exponent = int.from_bytes(key.public_exponent, 'little')
        if exponent != expected_exponent:
            log().warning(f"WARNING:\nDangerous RSA key! Public exponent should be {expected_exponent} "
                               f"but is {exponent}")

    return key


def hash_signing_key(signing_key, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    if isinstance(signing_key, ss.EcSigningKey):
        to_hash = signing_key.qx + signing_key.qy
    else:
        to_hash = signing_key.modulus + signing_key.public_exponent
    signing_key.hashed_key = calculate_hash(to_hash, hash_type, is_legacy)


def calculate_signature_r_s(signing_key, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    sig = signing_key.ec_key.sign(signing_key.hashed_key,
                                  ec.ECDSA(ss.SupportedSHAs.get_sha_class(hash_type, is_legacy)))
    r, s = utils.decode_dss_signature(sig)
    signing_key.signature_r = r.to_bytes(signing_key.coordinate_size, ss.ByteOrder.LITTLE.value)
    signing_key.signature_s = s.to_bytes(signing_key.coordinate_size, ss.ByteOrder.LITTLE.value)


def convert_rsa_key_format(key_file, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    stat = os.stat(key_file)
    with open_file(key_file, 'rb') as kfile:
        mm = mmap.mmap(-1, stat.st_size)
        mm.write(kfile.read())
        mm.seek(0)

        search = b'(11:private-key'
        pos = mm.find(search)

        mm.seek(pos)
        search = b'(1:e'  # search for exponent. I.e. this can be b'(1:e1:' or b'(1:e4:'
        pos = mm.find(search)
        offset = pos + len(search)
        exponent_size = int(mm[offset: offset + 1])
        offset = pos + len(b'(1:e1:')  # skip exponent marker
        public_exponent = mm[offset: offset + exponent_size].ljust(4, b'\x00')

        mm.seek(pos)
        search = b'(1:n256:'
        pos = mm.find(search)
        offset = pos + len(search)
        modulus = mm[offset: offset + 256]
        modulus = modulus[::-1]

        mm.seek(pos)
        search = b'(1:d256:'
        pos = mm.find(search)
        offset = pos + len(search)
        private_exponent = mm[offset: offset + 256]
        private_exponent = private_exponent[::-1]

        mm.seek(pos)
        search = b'(1:p128:'
        pos = mm.find(search)
        offset = pos + len(search)
        primep = mm[offset: offset + 128]
        primep = primep[::-1]

        mm.seek(pos)
        search = b'(1:q128:'
        pos = mm.find(search)
        offset = pos + len(search)
        primeq = mm[offset: offset + 128]
        primeq = primeq[::-1]

        signing_key = ss.RsaSigningKey()
        signing_key.modulus = modulus
        signing_key.public_exponent = public_exponent
        signing_key.private_exponent = private_exponent
        signing_key.prime_p = primep
        signing_key.prime_q = primeq

        n = int.from_bytes(modulus, 'little')
        e = int.from_bytes(public_exponent, 'little')
        d = int.from_bytes(private_exponent, 'little')
        p = int.from_bytes(primep, 'little')
        q = int.from_bytes(primeq, 'little')

        ppn = rsa.RSAPrivateNumbers(p, q, d, rsa.rsa_crt_dmp1(d, p), rsa.rsa_crt_dmq1(d, q), rsa.rsa_crt_iqmp(p, q),
                                    rsa.RSAPublicNumbers(e, n))
        pkey = ppn.private_key(backend=default_backend())
        signing_key.rsa_key = pkey
        hash_signing_key(signing_key, hash_type, is_legacy)
        return signing_key


def check_is_private_key(file_name):
    with open_file(file_name, 'rb') as kfile:
        private_key_header = b"PRIVATE"
        lines = kfile.readlines()
        if any(private_key_header in line for line in lines):
            return True
        return False


def process_private_key(data, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    pkey = serialization.load_pem_private_key(data, password=None, backend=default_backend())
    if isinstance(pkey, rsa.RSAPrivateKey):
        return process_private_rsa_key(pkey, hash_type, is_legacy)
    if isinstance(pkey, ec.EllipticCurvePrivateKey):
        return process_private_ec_key(pkey, hash_type, is_legacy)
    raise LibException("Unexpected error: unknown private key type detected.")


def process_private_rsa_key(pkey, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    signing_key = ss.RsaSigningKey()
    # Key size must be in full DWORDS, if a key is shorter than we have to round it up.
    key_size = math.ceil(pkey.key_size / 32) * 4  # key_size in bytes
    signing_key.rsa_key = pkey

    public_key = pkey.public_key()
    signing_key.modulus = public_key.public_numbers().n.to_bytes(key_size, 'little')
    signing_key.public_exponent = public_key.public_numbers().e.to_bytes(ss.RsaSigningKey.ExponentSize, 'little')

    hash_signing_key(signing_key, hash_type, is_legacy)

    signing_key.private_exponent = pkey.private_numbers().d.to_bytes(key_size, 'little')
    signing_key.prime_p = pkey.private_numbers().p.to_bytes(int(key_size / 2), 'little')
    signing_key.prime_q = pkey.private_numbers().q.to_bytes(int(key_size / 2), 'little')
    return signing_key


def process_private_ec_key(prv_key, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    signing_key = process_public_ec_key(prv_key.public_key(), hash_type, is_legacy)
    signing_key.ec_key = prv_key
    hash_signing_key(signing_key, hash_type, is_legacy)
    calculate_signature_r_s(signing_key, hash_type, is_legacy)
    return signing_key


def process_public_ec_key(pkey, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    public_key = ss.EcSigningKey()
    bytes_length = (pkey.curve.key_size + 7) // 8
    public_numbers = pkey.public_numbers()
    public_key.coordinate_size = bytes_length
    public_key.qx = public_numbers.x.to_bytes(bytes_length, 'little')
    public_key.qy = public_numbers.y.to_bytes(bytes_length, 'little')
    public_key.ec_key = pkey
    public_key.curve = pkey.curve.name
    hash_signing_key(public_key, hash_type, is_legacy)
    return public_key


def process_public_key(data, hash_type, is_legacy):
    public_key = serialization.load_pem_public_key(data, default_backend())
    if isinstance(public_key, rsa.RSAPublicKey):
        return process_public_rsa_key(public_key, hash_type, is_legacy)
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        return process_public_ec_key(public_key, hash_type, is_legacy)
    raise LibException("Unexpected error: unknown public key type detected.")


def process_public_rsa_key(pkey, hash_type, is_legacy):
    pub_num = pkey.public_numbers()
    public_key = ss.RsaSigningKey()
    key_size = pkey.key_size // 8  # key_size in bytes
    public_key.rsa_key = pkey
    public_key.modulus = pub_num.n.to_bytes(key_size, 'little')
    public_key.public_exponent = pub_num.e.to_bytes(ss.RsaSigningKey.ExponentSize, 'little')
    hash_signing_key(public_key, hash_type, is_legacy)
    return public_key


def process_openssl_key(file_name, hash_type: ss.SupportedSHAs.ShaType, is_legacy: bool):
    is_private = check_is_private_key(file_name)
    with open_file(file_name, 'rb') as kfile:
        data = kfile.read()
        try:
            if is_private:
                signing_key = process_private_key(data, hash_type, is_legacy)
            else:
                signing_key = process_public_key(data, hash_type, is_legacy)
        except (ValueError, IndexError, TypeError) as ex:
            raise LibException(ex.args[0]) from None

        return signing_key


def hashed_key_printer(signing_key, file_name):
    """Reads hash given in signing_key and prints it to file_name."""
    if not signing_key:
        return

    if isinstance(signing_key, bytes):
        txt_hashed_key = Converter.bytes_to_string(calculate_hash(signing_key, ss.SupportedSHAs.ShaType.SHA256, True))
        key_kind = 'AesKey'
        print(f'{key_kind} key hash: {txt_hashed_key}')
    else:
        txt_hashed_key = Converter.bytes_to_string(signing_key.hashed_key)
        key_kind = signing_key.key_type.value
        print(f'Key public part hash: {txt_hashed_key}')

    if file_name:
        FileManager.save_text_file(file_name, txt_hashed_key)
        print(f'{key_kind} key hash saved in file: {file_name}')


def unify_path(path: str):
    """Function which unifies path separators in the specified path."""
    return os.path.join(*re.compile(r"[\\/]").split(path))


def get_file_name_no_ext(file_name):
    """Returns file name without extension."""
    input_name = os.path.basename(file_name)
    return os.path.splitext(input_name)[0]


def get_file_ext(file_name):
    """Returns file extension including dot."""
    input_name = os.path.basename(file_name)
    return os.path.splitext(input_name)[1]


def last_index(list_, item_):
    """Returns last index of searched item in a list."""
    return len(list_) - 1 - list_[::-1].index(item_)


def align_value(value, alignment):
    if (value % alignment) != 0:
        difference = alignment - (value % alignment)
        return value + difference
    return value


def get_value_from_child_component(parent_component, tag_name):
    try:
        node = parent_component.get_child(tag_name)
    except ComponentException as e:
        raise LibException(f"Couldn't get node '{tag_name}' from '{parent_component.name}'") from e
    value = node.value
    if value is None:
        raise LibException(f'Value is not set in {parent_component.name}/{tag_name}')
    return value


def to_hex(value, size):
    if value is None:
        return None

    return hex(value & 2 ** (size * 8) - 1) if value < 0 else hex(value)


def bit_count(value):
    return len(bin(int(value, 0))[2:])


def get_min_max_values(size: int, signed: bool) -> Tuple[str, str]:
    str_min = "0x0"
    str_max = hex(maxsize)

    if size is not None:
        if size > 0:
            maximum = int(math.pow(2, size * 8))
            if signed:
                half = maximum // 2
                str_min = str(half * -1)
                str_max = str(half - 1)
            else:
                str_max = str(hex(maximum - 1))
        else:
            raise LibException("Can not generate minimum and maximum value if size is less than 1.")

    return str_min, str_max


def check_value_in_enum(value, enum_class):
    values = [item.value for item in enum_class]
    if value not in values:
        raise LibException(', '.join(values))


def parse_json_str(text):
    text = text.replace("\'", "\"")
    text = text.replace("&apos;", "\'")

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise JSONException(f'Incorrect json params definition: [{text}]') from e


def prepare_string_to_xml(value):
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;") \
        .replace("\0", "")


def get_item_from_structure(structure, key):
    if isinstance(structure, dict) and key in structure:
        return structure[key]
    if isinstance(structure, list):
        for element in structure:
            item = get_item_from_structure(element, key)
            if item is not None:
                return item
    if isinstance(structure, dict):
        for element in structure.values():
            item = get_item_from_structure(element, key)
            if item is not None:
                return item
    return None


def check_file_path(path, can_be_empty=True, throwing=True, restrict_types=None, print_warn=False):
    """
    Checks existence of a file and if it's of proper extension type and contains only printable ascii characters.
    :param path: String that specifies path to the file.
    :param can_be_empty: Indicates that path can be empty.
    :param throwing: Indicates whether function should raise IncorrectFileTypeException or
        FileDoesNotExistException when check failed.
    :param restrict_types: List of acceptable extension types.
    :param print_warn: Indicates whether function should print warning when check failed.
    :return: True if file exists and is of proper type, else False.
    """
    # we allow empty path or not according the flag can_be_empty
    is_exist = os.path.isfile(path) if path else False
    is_proper_type = (can_be_empty and not path) or (
            not restrict_types or os.path.splitext(path)[1][1:] in restrict_types)
    should_throw = (not can_be_empty and not path) or path
    valid_path = True
    try:
        check_for_illegal_characters(path)
    except InvalidFilePathException:
        valid_path = False
    if should_throw and not is_exist:
        if throwing:
            raise FileDoesNotExistException(path)
        if print_warn:
            log().warning(FileDoesNotExistException.get_message(path=os.path.abspath(path)))
        return False
    if not is_proper_type:
        if throwing:
            raise IncorrectFileTypeException(path, restrict_types)
        if print_warn:
            log().warning(IncorrectFileTypeException.get_message(path=os.path.abspath(path),
                                                                 accepted_types=", ".join(restrict_types)))
        return False
    elif not valid_path:
        if throwing:
            raise InvalidFilePathException(path)
        if print_warn:
            log().warning(InvalidFilePathException.get_message(path=path))
        return False
    elif not is_exist:
        return False
    return True


def check_for_illegal_characters(*paths):
    """Checks every string given in function arguments for characters illegal in path."""
    regex = re.compile(ILLEGAL_PATH_CHARACTERS)
    for path in paths:
        if regex.search(os.path.basename(path)):
            raise InvalidFilePathException(path)
        if not path.isprintable() or not path.isascii():
            raise InvalidFilePathException(path)


def print_header(name, version, copyright_date_range=None):
    """
    This function will log the currently run tool header (to all logs).
    :param name: Name of the tool
    :param version: Version of the tool
    :param copyright_date_range: (optional) Date range to be included in copyright (e.g. 2019-2022)
    """
    copyright_date = copyright_date_range if copyright_date_range else datetime.now().year
    current_date = datetime.now().strftime("%d/%m/%Y - %H:%M")
    copyright_header = '\n\n=============================================================================\n' \
                       f'{name} ' \
                       f'Version: {version}\n' \
                       f'Copyright (c) {copyright_date}, Intel Corporation. All rights reserved.\n' \
                       f'{current_date}\n' \
                       '=============================================================================\n'
    ColorPrint.save_to_all_logs(copyright_header)


def is_python_ver_satisfying(required_python: Tuple[int, int]):
    if sys.version_info[:2] < required_python:
        print(f'Python version {",".join([str(num) for num in required_python])} or greater is necessary to run.')
        return False
    return True


def convert_to_limited_string(input_data: Any, max_characters: int = 350):
    """
    Converts any input to limited string.

    :param input_data: any input to be converted to string
    :param max_characters: maximum length of result string;
                           default value based on typical call (optional)

    :return: limited string representation of given input
    """
    output_string = str(input_data)
    if len(output_string) > max_characters:
        output_string = output_string[:max_characters] + "..."

    return output_string


class XmlAttrType(Enum):
    # pylint: disable=unnecessary-lambda-assignment
    STRING = lambda s: s
    PATH = lambda s: s
    VERSION = Converter.string_to_version
    BOOL = Converter.string_to_bool
    INT = Converter.string_to_int
    # pylint: enable=unnecessary-lambda-assignment


class XmlAttr:
    id = 'name'

    def __init__(self, **kwargs):
        self.name = kwargs.get(self.id, '')
        self.is_required = kwargs.get('is_required', True)
        self.node = kwargs.get('xml_node', None)
        self.attr_type = kwargs.get('attr_type', XmlAttrType.STRING)
        self.default = kwargs.get('default', None)

    @property
    def value(self):
        if self.name in self.node.attrib:
            return partial(self.attr_type, self.node.attrib[self.name])()
        if self.is_required:
            raise XmlAttrException(f"Cannot find required attribute '{self.name}' at node: {self.node.tag}")
        return self.default


@dataclass
class MapData:
    """Keeps parsed map data start, offset, length, intent, map name"""
    offset: int
    length: int
    indent: int
    map_name: str
