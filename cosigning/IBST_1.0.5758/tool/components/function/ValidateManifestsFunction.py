#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2020-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""

from .IManifestsListFunction import IManifestsListFunction
from ...LibException import ComponentException
from ...Converter import Converter
from ...LibConfig import LibConfig
from ...ColorPrint import log


class ValidateManifestsFunction(IManifestsListFunction):

    def _build(self, buffer):
        # When only validating manifests then we don't need any output
        if LibConfig.generateOutput is None:
            LibConfig.generateOutput = False
        super()._build(buffer)
        manifests_in_binary = {manifest.index: manifest for manifest in self._find_manifests(buffer)}
        validated_manifests_count = 0
        for manifest_from_xml in self._scan_manifests_list(False):
            if manifest_from_xml.index not in manifests_in_binary:
                raise ComponentException(f"Loaded binary doesn't have manifest with index: {manifest_from_xml.index}",
                                         self.name)
            manifest_in_binary = manifests_in_binary[manifest_from_xml.index]
            if manifest_from_xml.manifest_offset != manifest_in_binary.manifest_offset:
                raise ComponentException(f"Manifest {manifest_from_xml.index} is at wrong offset:"
                                         f"\n{hex(manifest_from_xml.manifest_offset)} (in XML)"
                                         f"\n{hex(manifest_in_binary.manifest_offset)} (in binary)", self.name)
            if manifest_from_xml.manifest_hash != manifest_in_binary.manifest_hash:
                raise ComponentException(f"Manifest {manifest_from_xml.index} has different hash: "
                                         f"\n{Converter.bytes_to_string(manifest_from_xml.manifest_hash)} (in XML)"
                                         f"\n{Converter.bytes_to_string(manifest_in_binary.manifest_hash)} (in binary)",
                                         self.name)
            if manifest_from_xml.public_key_hash != manifest_in_binary.public_key_hash:
                raise ComponentException(f"Manifest {manifest_from_xml.index} has different public key hash: "
                                         f"\n{Converter.bytes_to_string(manifest_from_xml.public_key_hash)} (in XML)"
                                         f"\n{Converter.bytes_to_string(manifest_in_binary.public_key_hash)} "
                                         f"(in binary)", self.name)
            if manifest_from_xml.post_pv != manifest_in_binary.post_pv:
                raise ComponentException(f"Manifest {manifest_from_xml.index} has different Post PV flag:"
                                         f"\n{manifest_from_xml.post_pv} (in XML)"
                                         f"\n{manifest_in_binary.post_pv} (in binary)", self.name)
            validated_manifests_count += 1

        log().success(f'Validated {validated_manifests_count} '
                           f'{"manifests" if validated_manifests_count > 1 else "manifest"}.')
        self._move_buffer_to_end(buffer)
