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

import sys
from tool import ibst_main  # pylint: disable=import-error


def main():
    if __name__ == '__main__':
        is_exe = bool(getattr(sys, 'frozen', False))
        app_file = sys.executable if is_exe else __file__
        sys.exit(ibst_main.main(app_file, sys.argv[1:]))


main()
