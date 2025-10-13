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

from .IComponent import IComponent
from ..LibException import ComponentException, LibException
from ..utils import validate_file
from ..structures import Buffer
from mmap import ACCESS_READ
from ..components.FileComponent import FileComponent
from ..components.StringComponent import StringComponent


class DecompositionComponent(IComponent):
    decompositionTag = 'decomposition'
    file_dep_path = None

    fileTag = 'file'

    def __init__(self, xml_node, **kwargs):
        super()._init_properties(xml_node, kwargs)
        self.file_dep_path = xml_node.get(self.fileTag)
        if self.file_dep_path is None:
            raise ComponentException("File tag missing in decomposition node")
        if not isinstance(self.expr_engine.calculate_component_from_path(self.file_dep_path), (FileComponent, StringComponent)):
            raise ComponentException("Cannot decompose specified component type")
        file_name = self.calculate_value(self.file_dep_path, allow_calculate=True)
        try:
            validate_file(file_name)
        except LibException as ex:
            if self.is_gui:
                self.error_message = str(ex)
                return
            self.error_message = str(ex)
            raise ComponentException("Cannot open file: '{}' ".format(file_name))
        with open(file_name, "rb") as f:
            buffer = Buffer(f.fileno(), 0, access=ACCESS_READ)
            kwargs['buffer'] = buffer
            super().__init__(xml_node, **kwargs)
            buffer.close()

    def _copy_to(self, dst):
        raise ComponentException("Using in dependency expressions is not supported: " + self.name)
