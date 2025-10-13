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
from .IOutputManifestsFunction import IOutputManifestsFunction
from .IManifestsListFunction import IManifestsListFunction
from ...LibException import ComponentException
from ...LibConfig import LibConfig
from ...ColorPrint import log


class ImportManifestsFunction(IOutputManifestsFunction, IManifestsListFunction):
    def _build(self, buffer):
        # importing manifests needs output.
        # We set it explicitly because this function is used with ValidateManifestFunction which doesn't need output
        LibConfig.generateOutput = True
        super()._build(buffer)
        manifests_in_binary = {manifest.index: manifest for manifest in self._find_manifests(buffer)}
        imported_manifests_count = 0
        for manifest_from_xml in self._scan_manifests_list():
            if manifest_from_xml.index not in manifests_in_binary:
                raise ComponentException(f"Loaded binary doesn't have manifest with index: {manifest_from_xml.index}",
                                         self.name)
            manifest_in_binary = manifests_in_binary[manifest_from_xml.index]
            if len(manifest_from_xml.manifest) != len(manifest_in_binary.manifest):
                raise ComponentException(f"Cannot import manifest {manifest_from_xml.index}, lengths don't match:"
                                         f"\n{hex(len(manifest_from_xml.manifest))} (to import)"
                                         f"\n{hex(len(manifest_in_binary.manifest))} (original)",
                                         self.name)
            if manifest_from_xml.manifest_offset != manifest_in_binary.manifest_offset:
                raise ComponentException(f"Cannot import manifest {manifest_from_xml.index}, offsets should be the same"
                                         f" but are not:"
                                         f"\n{hex(manifest_from_xml.manifest_offset)} (to import)"
                                         f"\n{hex(manifest_in_binary.manifest_offset)} (original)", self.name)
            buffer.seek(manifest_in_binary.manifest_offset)
            buffer.write(manifest_from_xml.manifest)
            imported_manifests_count += 1

        log().success(f'Imported {imported_manifests_count} '
                           f'{"manifests" if imported_manifests_count > 1 else "manifest"}.')
        self._move_buffer_to_end(buffer)
