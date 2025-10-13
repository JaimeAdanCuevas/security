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


import os.path
import hashlib
import mmap
import re
import json
from math import ceil
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from .LibException import LibException, ComponentException
from . import structures as ss
from .Converter import Converter
from .LibConfig import LibConfig
from .exceptions import JSONException


#
# Function calculate hash for buffer using by default SHA256 method
#
def calculate_hash(buffer, hash_type=ss.ShaType.SHA256):
    if hash_type == ss.ShaType.SHA256:
        return hashlib.sha256(buffer).digest()
    elif hash_type == ss.ShaType.SHA512:
        return hashlib.sha512(buffer).digest()

    raise LibException('Hash type not supported')


def set_nth_bit(length, bit):
    arr = bytearray(length)
    bbyte = bit // 8
    bit_in_byte = bit - 8 * bbyte
    arr[length - 1 - bbyte] |= 1 << bit_in_byte

    return bytes(arr)


def process_key_file(file_name, hash_type):
    if not os.path.isfile(file_name) and not os.access(file_name, os.R_OK):
        msg = 'Could not open key file - "{}"'.format(file_name)
        raise LibException(msg)

    use_dbg_key = False

    with open(file_name, 'rb') as kfile:
        line = b'(8:sequence'
        buffer = kfile.read(len(line))
        if line == buffer:
            use_dbg_key = True

    if use_dbg_key:
        # convert the raw data into the right structure
        key = convert_rsa_key_format(file_name, hash_type)
    else:
        key = process_openssl_key(file_name, hash_type)

    return key


def hash_signing_key(signing_key, hash_type):
    to_hash = signing_key.modulus + signing_key.public_exponent
    signing_key.hashed_key = calculate_hash(to_hash, hash_type)


def convert_rsa_key_format(key_file, hash_type):
    stat = os.stat(key_file)
    with open(key_file, 'rb') as kfile:
        mm = mmap.mmap(-1, stat.st_size)
        mm.write(kfile.read())
        mm.seek(0)

        search = b'(11:private-key'
        pos = mm.find(search)

        mm.seek(pos)
        search = b'(1:e1:'
        pos = mm.find(search)
        offset = pos + len(search)
        public_exponent = mm[offset: offset + 1].ljust(4, b'\x00')

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

        signing_key = ss.SigningKey()
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

        ppn = rsa.RSAPrivateNumbers(p, q, d,
                                    rsa.rsa_crt_dmp1(d, p),
                                    rsa.rsa_crt_dmq1(d, q),
                                    rsa.rsa_crt_iqmp(p, q),
                                    rsa.RSAPublicNumbers(e, n))
        pkey = ppn.private_key(backend=default_backend())
        signing_key.rsa_key = pkey
        hash_signing_key(signing_key, hash_type)

        return signing_key


def check_is_private_key(file_name):
    with open(file_name, 'rb') as kfile:
        private_key_header = b"PRIVATE"
        header = kfile.readline()
        if private_key_header in header:
            return True
        return False


def process_private_key(data, hash_type):
    pkey = serialization.load_pem_private_key(data, password=None, backend=default_backend())
    signing_key = ss.SigningKey()
    # Key size must be in full DWORDS, if a key is shorter then we have to round it up.
    key_size = ceil(pkey.key_size / 32) * 4  # key_size in bytes
    signing_key.rsa_key = pkey

    public_key = pkey.public_key()
    signing_key.modulus = public_key.public_numbers().n.to_bytes(key_size, 'little')
    signing_key.public_exponent = public_key.public_numbers().e.to_bytes(ss.SigningKey.ExponentSize, 'little')

    hash_signing_key(signing_key, hash_type)

    signing_key.private_exponent = pkey.private_numbers().d.to_bytes(key_size, 'little')
    signing_key.prime_p = pkey.private_numbers().p.to_bytes(int(key_size / 2), 'little')
    signing_key.prime_q = pkey.private_numbers().q.to_bytes(int(key_size / 2), 'little')
    return signing_key


def process_public_key(data, hash_type):
    pkey = serialization.load_pem_public_key(data, default_backend())
    pub_num = pkey.public_numbers()
    public_key = ss.SigningKey()
    key_size = pkey.key_size // 8  # key_size in bytes
    public_key.rsa_key = pkey
    public_key.modulus = pub_num.n.to_bytes(key_size, 'little')
    public_key.public_exponent = pub_num.e.to_bytes(ss.SigningKey.ExponentSize, 'little')
    hash_signing_key(public_key, hash_type)
    return public_key


def process_openssl_key(file_name, hash_type):
    is_private = check_is_private_key(file_name)
    with open(file_name, 'rb') as kfile:
        data = kfile.read()
        try:
            if is_private:
                signing_key = process_private_key(data, hash_type)
            else:
                signing_key = process_public_key(data, hash_type)
        except (ValueError, IndexError, TypeError) as ex:
            raise LibException(str(ex))

        return signing_key


#
# Function prints (and writes to file) hash of signing key
#
def hashed_key_printer(signing_key, file_name):
    if not signing_key:
        return

    txt_hashed_key = Converter.bytes_to_string(signing_key.hashed_key)
    key_kind = signing_key.key_type.value

    print('{} key hash: {}'.format(key_kind, txt_hashed_key))
    if file_name:
        with open(file_name, mode='w') as f:
            f.write(txt_hashed_key)
        print('{} key hash saved in file: {}'.format(key_kind, file_name))


#
#   Function validating xml based on xml scheme and schematron included to source
#
def validate_xml(xml):
    from lxml import etree
    try:
        xml_file = open(file=xml, mode="r", encoding="utf-8-sig")
    except IOError as err:
        print(err)
        return False

    xml_doc = etree.parse(xml_file)
    if xml_file:
        xml_file.close()
    return validate_xml_tree(xml_doc)


def validate_xml_str(xml_doc_str):
    from lxml import etree
    xml_doc = etree.fromstring(xml_doc_str)
    return validate_xml_tree(xml_doc)


def validate_xml_tree(xml_doc):
    from lxml import etree, isoschematron
    schema_file = LibConfig.schemaPath
    try:
        schema_file = open(file=schema_file, mode="r", encoding="utf-8-sig")
    except IOError as err:
        print(err)
        return False

    schema_doc = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_doc)
    if schema_file:
        schema_file.close()
    schematron = isoschematron.Schematron(etree=schema_doc,
                                          error_finder=isoschematron.Schematron.ASSERTS_AND_REPORTS)
    if not validate_with(schema, xml_doc):
        return False
    return validate_with(schematron, xml_doc)

def validate_with(validator, xml_doc):
    result = validator.validate(xml_doc)
    if not result:
        log = validator.error_log
        print(log.last_error)
        return False
    return True


#
#   Function validating whether file with given path is ok
#
def validate_file(file):
    if not os.path.isfile(file) and not os.access(file, os.R_OK):
        raise LibException("File '{}' could not be opened!".format(file))

#
#   Function which unifies path separators in the specified path
#
def unify_path(path: str):
    return os.path.join(*re.compile(r"[\\/]").split(path))


#
#   Function returns file name without extension
#
def get_file_name_no_ext(file_name):
    input_name = os.path.basename(file_name)
    return os.path.splitext(input_name)[0]


#
#   Function returns file extension including dot
#
def get_file_ext(file_name):
    input_name = os.path.basename(file_name)
    return os.path.splitext(input_name)[1]


#
#    Function returns last index of searched item in a list
#
def last_index(list_, item_):
    return len(list_) - 1 - list_[::-1].index(item_)


def align_value(value, alignment):
    if (value % alignment) != 0:
        difference = alignment - (value % alignment)
        return value + difference
    return value


def get_value_from_child_component(parent_component, tag_name):
    try:
        node = parent_component.get_child(tag_name)
    except ComponentException:
        raise LibException("Couldn't get node '{}' from '{}'".format(tag_name, parent_component.name))
    value = node.value
    if value is None:
        raise LibException('Value is not set in {}/{}'.format(parent_component.name, tag_name))
    return value


def to_hex(value, size):
    if value is None:
        return None

    return hex(value & 2 ** (size * 8) - 1) if value < 0 else hex(value)


def bit_count(value):
    return len(bin(int(value, 0))[2:])


def check_value_in_enum(value, enum_class):
    values = [item.value for item in enum_class]
    if value not in values:
        raise LibException(', '.join(values))


def parse_json_str(text):
    text = text.replace("\'", "\"")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise JSONException(f'Incorrect json params definition: [{text}]')
