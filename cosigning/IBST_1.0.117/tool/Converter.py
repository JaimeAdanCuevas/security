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

import binascii
from distutils.version import StrictVersion
from .LibException import LibException


class Converter:
    @staticmethod
    def string_to_int(string_value, safe=True):
        if "0x" in string_value:
            base = 16
        else:
            base = 10

        try:
            return int(string_value, base)
        except ValueError:
            if safe:
                raise LibException("Cannot convert '{}' to integer.".format(string_value))
            else:
                raise # TODO: consider why do we need the safe flag here if we raise exceptions regardless

    boolValues = {"false": False,
                  "true": True}

    @classmethod
    def string_to_bool(cls, string_value: str):
        if not string_value:
            return True
        string_value = string_value.lower()
        if string_value in cls.boolValues:
            return cls.boolValues[string_value]

        raise ValueError("Cannot convert '{}' to boolean.".format(string_value))

    @staticmethod
    def string_to_bytes(string_value):
        # firstly we don't want to have any '0x'
        if "0x" in string_value:
            string_value = string_value.replace("0x", "")
        # secondly deal with odd length string
        if (len(string_value) % 2) != 0:
            string_value = "0" + string_value

        try:
            return binascii.unhexlify(string_value)
        except binascii.Error as ex:
            raise LibException("{} : {}".format(str(ex), string_value))

    @staticmethod
    def bytes_to_string(bytes_value):
        return binascii.hexlify(bytes_value).decode().upper()

    @staticmethod
    def string_to_version(string_value):
        try:
            ver = StrictVersion(string_value)
            return ver
        except ValueError:
            raise ValueError('Could not parse value: %s' % string_value)
