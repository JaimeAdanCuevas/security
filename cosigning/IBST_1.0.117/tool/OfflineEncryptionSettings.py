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

from collections import namedtuple
from .utils import get_value_from_child_component


class OfflineEncryptionSettings:
    class Tags:
        enabled = 'enabled'
        loadPhase = 'load_encrypted_data'
        storeDir = 'store_dir'

    enabled = None
    load_phase = None
    store_dir = None

    def __init__(self, settings_component):
        self.enabled = bool(get_value_from_child_component(settings_component, self.Tags.enabled))
        self.load_phase = bool(get_value_from_child_component(settings_component, self.Tags.loadPhase))
        self.store_dir = get_value_from_child_component(settings_component, self.Tags.storeDir)

    @staticmethod
    def get_files_names(module_name):
        extensions = ['unencrypted', 'encrypted', 'iv']
        FileNames = namedtuple('FileNames', ' '.join(extensions))
        return FileNames(*[module_name + '.' + ext for ext in extensions])

