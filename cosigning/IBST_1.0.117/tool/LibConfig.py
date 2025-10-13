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


class LibConfig:
    settingsTag = None
    overridesTag = None
    decompositionTag = "decomposition"
    byteArrayPaddingValue = None
    rootTag = None
    coreDir = None
    runFrom = None
    maxBufferSize = None
    pathSeparator = "/"
    schemaPath = None
    is_gui = False
    is_verbose = True

