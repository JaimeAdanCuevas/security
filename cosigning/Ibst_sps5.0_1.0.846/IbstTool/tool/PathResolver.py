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
import os
import xml.etree.ElementTree as Et
from .components.IComponent import IComponent
from .LibConfig import LibConfig
from .utils import unify_path


class PathResolver(object):
    _tokenChar = "$"
    pluginDirToken = _tokenChar + "PluginDir"

    def __init__(self, core_dir: str, plugin_dir: str = "."):
        self._core_dir = core_dir
        self._plugin_dir = plugin_dir
        self._plugin_dir_rel = os.path.relpath(plugin_dir, core_dir)

        self._token_map = {
            PathResolver.pluginDirToken: self._plugin_dir_rel,
        }

    @classmethod
    def is_unresolved(cls, value: str):
        return value.startswith(cls._tokenChar)

    def resolve_path(self, value: str):
        for k, v in self._token_map.items():
            if value.find(k) >= 0:
                value = value.replace(k, v)
        return value

    def resolve_paths(self, tree: Et.ElementTree, root_name):
        nodes = tree.find(".//" + root_name)
        for config_successor in nodes.iter():
            value = None
            if config_successor.get(IComponent.valueTag):
                value = config_successor.attrib[IComponent.valueTag]
            if value and self.is_unresolved(value):
                value = self.resolve_path(value)
                config_successor.attrib[IComponent.valueTag] = unify_path(value)
