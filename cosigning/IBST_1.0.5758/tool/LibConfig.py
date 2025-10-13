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

from enum import Enum


class LoadingUserXml:
    """Context manager keeping track of isLoadingUserXml property of LibConfig."""
    def __enter__(self):
        LibConfig.isLoadingUserXml = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        LibConfig.isLoadingUserXml = False


class LibConfig:
    class ToolType(Enum):
        UNKNOWN = None
        IBST = 'IBST'
        FIT = 'FIT'

    configurationTag = 'configuration'
    settingsTag = None
    layoutTag = "layout"
    decompositionTag = "decomposition"
    coreTag = "core"
    overridesTag = None
    defaultPaddingValue = None
    rootTag = None
    runFrom = None
    maxBufferSize = None
    pathSeparator = "/"
    schemaPath = None
    appDir = None
    logsDir = None
    isGui = False
    isDecompose = False
    isMerge = False
    isSecurity = False
    isLoadingUserXml = False
    decompositionPath = None
    isVerbose = False
    enableRegions = 'enable_regions'
    exitCode = 0
    '''AllowEmptyConfiguration and isOrchestrator variables are used in Orchestrator do not remove them'''
    allowEmptyConfiguration = False
    isOrchestrator = False
    isAccessCheckSkipped = False
    isDirAclSet = False
    saveLog = False
    '''
    generateOutput - if it's None then we use default behaviour. Setting True / False is a way of communication that
    some part of the tool explicitly says that output is not needed or that it is needed.
    (e.g. ImportManifestFunction / VerifyManifestFunction)
    '''
    generateOutput: bool = None
    layoutsPath: str = ''
    pluginsPath: str = ''
    skipSchemaValidation = False
    toolType: ToolType = ToolType.UNKNOWN
    legacyMap = False
    defaultVersion = '1.0.0'
    serverPortString = ''
    namedPipeRandom = ''
