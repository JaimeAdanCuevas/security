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
import os
from lxml.etree import Element  # nosec - used just as type annotation
from .components.IComponent import IComponent
from .utils import unify_path


class PathResolver:
    _tokenChar = "$"
    _cryptoDirName = "cryptography"
    pluginDirToken = _tokenChar + "PluginDir"
    cryptoDirToken = _tokenChar + "CryptoDir"

    def __init__(self, core_dir: str, plugin_dir: str = "."):
        self._core_dir = core_dir
        self._plugin_dir = plugin_dir
        self._plugin_dir_rel = os.path.relpath(plugin_dir, core_dir)
        self._crypto_dir = self._cryptoDirName

        if plugin_dir != ".":
            self._crypto_dir = os.path.join(self._crypto_dir, os.path.basename(plugin_dir))

        self._token_map = {
            PathResolver.pluginDirToken: self._plugin_dir_rel,
            PathResolver.cryptoDirToken: self._crypto_dir
        }

    @classmethod
    def is_unresolved(cls, value: str):
        return value.startswith(cls._tokenChar)

    def resolve_path(self, value: str):
        for k, v in self._token_map.items():
            if value.find(k) >= 0:
                value = value.replace(k, v)
        return value

    def resolve_paths(self, root: Element, root_name):
        nodes = root.find(".//" + root_name)
        for config_successor in nodes.iter():
            value = None
            if config_successor.get(IComponent.Tags.VALUE):
                value = config_successor.attrib[IComponent.Tags.VALUE]
            if value and self.is_unresolved(value):
                value = self.resolve_path(value)
                config_successor.attrib[IComponent.Tags.VALUE] = unify_path(value)
