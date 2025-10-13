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

from os import stat, path
from mmap import ACCESS_READ

from .ByteArrayComponent import ByteArrayComponent
from ..ColorPrint import log
from ..Converter import Converter
from .IComponent import IComponent
from ..FileManager import FileManager
from ..LibConfig import LibConfig
from ..LibException import ComponentException, LibException, FileException, WrongDecompositionFileException, \
    DecompositionFileNotGiven
from ..structures import Buffer
from ..FileOpener import open_file


class DecompositionComponent(IComponent):
    class Tags(IComponent.Tags):
        FILE = 'file'
        OUTPUT_SUFFIX = 'output_suffix'
        RANDOM_ACCESS = 'random_access'

    file_dep_path = None
    file_name = None
    output_suffix = None

    def __init__(self, xml_node, **kwargs):
        kwargs['is_decomposition_node'] = True
        self._init_properties(xml_node, kwargs)
        self._parse_attributes(xml_node)
        self.append_to_parent()
        if self._skip_calculates:
            self._handle_skip_calculates_scenario(xml_node, **kwargs)
        elif self.file_dep_path is None:
            self._handle_no_input_file_scenario(xml_node, **kwargs)
        else:
            self.file_name = self.calculate_value(self.file_dep_path, allow_calculate=True, build_process=True)
            if not isinstance(self.file_name, str):
                raise ComponentException(f"'{self.Tags.FILE} must resolve to a string value'")
            if not self.file_name:
                # if path is empty then we skip decomposition
                return
            self._validate_decomposition_file_path()
            self._handle_decomposition_file(xml_node, kwargs)
            parent_file_mtime = self._get_parent_file_mtime(kwargs)
            self.input_file_mtime = stat(path.abspath(self.file_name), follow_symlinks=False).st_mtime
            self._resolve_decomposition_calculates(parent_file_mtime)

    def _init_properties(self, xml_node, kwargs):
        super()._init_properties(xml_node, kwargs)
        self.decomposition_xml_node = xml_node  # this is used by ExportManifestFunction
        self.input_file_mtime = 0

    def _parse_attributes(self, xml_node):
        self.output_suffix = self._parse_attribute(xml_node, self.Tags.OUTPUT_SUFFIX, False, None)
        self.file_dep_path = self._parse_attribute(xml_node, self.Tags.FILE, False, None)
        self.random_access = self._parse_attribute(xml_node, self.Tags.RANDOM_ACCESS, False, False)

    def _handle_skip_calculates_scenario(self, xml_node, **kwargs):
        # Decomposition node should parse children and not load input file in case of full decomposition
        super().__init__(xml_node, **kwargs)
        self._parse_children(xml_node, **kwargs)

    def _handle_no_input_file_scenario(self, xml_node, **kwargs):
        # If we don't specify file input for decomposition then we will use this node for other purposes
        # (e.g. decomposing some binary data that we get later)
        self.enabled = True
        super().__init__(xml_node, **kwargs)

    def _validate_decomposition_file_path(self):
        try:
            FileManager.validate_path_to_open(self.file_name)
        except FileException as ex:
            try:
                # Get name of referenced component as "decomposition" itself isn't clear source of error for the user.
                component = self.calculate_value('.'.join(self.file_dep_path.split('.')[:-1]))
                component_name = component.display_name
            except ComponentException:
                component_name = self.name
            self.error_message = str(ex)
            raise ComponentException(str(ex), component_name) from None

    def _handle_decomposition_file(self, xml_node, kwargs):
        with open_file(self.file_name, "rb") as f:
            buffer = Buffer(f.fileno(), 0, access=ACCESS_READ)
            self._validate_file_size(xml_node, buffer)
            kwargs['buffer'] = buffer
            kwargs['random_access'] = self.random_access
            try:
                super().__init__(xml_node, **kwargs)
                self._validate_descendants()
            except LibException as ex:
                path_split = self.file_dep_path.rsplit('.')[0]
                log().debug(f"{ex}")
                raise WrongDecompositionFileException(self.file_name, path_split, self.name) from ex
            finally:
                buffer.close()

    def _validate_descendants(self):
        for descendant in self.descendants:
            descendant.check_validate_formula()

    def _validate_file_size(self, xml_node, buffer):
        declared_size = xml_node.attrib.get('size', None)

        if declared_size:
            size_limit = Converter.string_to_int(declared_size)
            file_size = buffer.max_size

            if size_limit != file_size:
                raise ComponentException(
                    f"Decomposition file size is not equal to expected size. Expected size is {size_limit} and "
                    f"{self.file_name} size is: {file_size}")

    def _get_child(self, child_name):
        if self.buffer is None and not self._skip_calculates:
            path_split = self.file_dep_path.rsplit('.')[0] if self.file_dep_path else ''
            raise DecompositionFileNotGiven(f'File for decomposition was not set in {path_split}', self.name)
        return super()._get_child(child_name)

    def is_enabled(self):
        if self.enabled is None:
            return bool(self.file_name)
        return self.enabled

    def _copy_to(self, dst):
        raise ComponentException("Using in dependency expressions is not supported: " + self.name)

    def _parse_basic_attributes(self, xml_node):
        super()._parse_basic_attributes(xml_node)
        if self.buffer is not None:
            self.buffer.seek(0)

    @staticmethod
    def _get_parent_file_mtime(kwargs):
        if 'parent' in kwargs:
            return next((child.input_file_mtime for child in reversed(kwargs['parent'].children) if
                         isinstance(child, DecompositionComponent)), 0)
        return 0

    def _resolve_decomposition_calculates(self, old_file_mtime):
        if LibConfig.configurationTag not in self.root_component.children_by_name:
            return

        from library.ConfigData import ConfigData  # pylint: disable=import-outside-toplevel
        settings_references = [s for s in ConfigData(self.root_component.children_by_name[LibConfig.configurationTag])
                               .settings.values() if s.decomposition_reference()]
        file_reloaded = self.input_file_mtime != old_file_mtime

        if not settings_references or not file_reloaded:
            return

        for s in settings_references:
            if not s.is_overwritten:
                s.set_value(s.calculate_value(s.value_formula))
                if s.display_user_set_value and isinstance(s, ByteArrayComponent):
                    s.user_set_value = Converter.bytes_to_string(s.value)
            else:
                s.is_overwritten = not s.is_overwritten
