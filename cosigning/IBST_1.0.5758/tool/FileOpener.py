# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2022-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
import builtins
import os
from contextlib import contextmanager, closing

from .LibException import SymlinkException


# pylint: disable=unspecified-encoding
@contextmanager
def open_file(path, *args, **kwargs):
    if os.path.islink(path):
        raise SymlinkException(path)

    file = builtins.open(path, *args, **kwargs)
    with closing(file):
        yield file
