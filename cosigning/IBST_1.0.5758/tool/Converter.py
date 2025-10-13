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

import binascii
from datetime import datetime, date
from typing import Optional
from packaging.version import Version

from .LibException import LibException


class Converter:
    @staticmethod
    def no_conversion(value):
        return value

    @staticmethod
    def string_to_int(string_value: str):
        is_hex_string = "0x" in string_value
        if is_hex_string:
            base = 16
        else:
            base = 10

        try:
            if '-' not in string_value and not string_value.isdigit() and not is_hex_string:
                raise LibException(f"Cannot convert float string '{string_value} to integer.")
            return int(string_value, base)
        except ValueError as e:
            raise LibException(f"Cannot convert '{string_value}' to integer.") from e

    boolValues = {"false": False,
                  "true": True}
    boolInt = {1: True,
               0: False}

    @classmethod
    def string_to_bool(cls, string_value: str, can_be_int=False):
        if not string_value:
            return True
        string_value = string_value.lower().strip()
        if string_value in cls.boolValues:
            return cls.boolValues[string_value]
        if can_be_int:
            try:
                value = Converter.string_to_int(string_value)
                if value in cls.boolInt:
                    return cls.boolInt[value]
            except LibException:
                pass
        raise ValueError(f"Cannot convert '{string_value}' to boolean.")

    @staticmethod
    def string_to_bytes(string_value: str):
        not_modified_value = string_value
        # firstly we don't want to have any '0x'
        if "0x" in string_value:
            string_value = string_value.replace("0x", "")
        # secondly deal with odd length string
        if (len(string_value) % 2) != 0:
            string_value = "0" + string_value

        try:
            return binascii.unhexlify(string_value)
        except binascii.Error as ex:
            raise LibException(f"{str(ex)} : '{not_modified_value}'") from None

    @staticmethod
    def bytes_to_string(bytes_value: bytes):
        return binascii.hexlify(bytes_value).decode().upper()

    @staticmethod
    def bytes_to_hex_string(bytes_value: bytes):
        string_value = Converter.bytes_to_string(bytes_value)
        hex_string = "0x" + string_value.lstrip("0")
        return hex_string

    @staticmethod
    def bytes_to_date(bytes_value: bytes) -> date:
        """Converts date bytes in YYYY MM DD format to date."""
        date_str = f'{bytes_value[2:4][::-1].hex()}-{bytes_value[1:2].hex()}-{bytes_value[0:1].hex()}'
        date_conv = datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_conv

    @staticmethod
    def string_to_version(string_value):
        try:
            ver = Version(string_value)
            return ver
        except ValueError as e:
            raise ValueError(f'Could not parse value: {string_value}.') from e

    @staticmethod
    def to_bytes(value, size, byte_order='little'):
        if isinstance(value, str):
            return Converter.string_to_bytes(value)
        if isinstance(value, int):
            return value.to_bytes(size, byteorder=byte_order)
        if isinstance(value, bytes):
            return value
        raise LibException(f"Cannot convert '{value}' to bytes.")

    @staticmethod
    def inner_string(element: str) -> Optional[str]:
        """
        Checks if given formula element should be treated as a string, by checking if it starts and ends with quotes.
        Used when we want to mark part of larger formula as a string.
        """
        quotes = ['"', "'"]
        for quote in quotes:
            if element.startswith(quote) and element.endswith(quote):
                string = element[1:-1]
                # string value cannot have unescaped quotes in the middle
                index = string.find(quote)
                while index != -1:
                    if index == 0 or string[index - 1] != '\\':
                        raise ValueError(f"Unescaped {quote} character inside string formula.")
                    backslash_count = 1
                    i = index - 2
                    while string[i] == '\\' and i >= 0:
                        backslash_count += 1
                        i -= 1
                    if not backslash_count % 2:
                        raise ValueError(f"Unescaped {quote} character inside string formula.")
                    index = string.find(quote, index + 1)
                string = string.replace('\\\\', '\\').replace(f'\\{quote}', quote)
                return string
        raise LibException(f"Cannot parse \"{element}\".")
