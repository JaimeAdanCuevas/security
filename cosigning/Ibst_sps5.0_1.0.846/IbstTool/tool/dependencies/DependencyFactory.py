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
from .Dependency import Dependency
from .GetDependency import GetDependency
from .SetDependency import SetDependency
from .SwitchDependency import SwitchDependency
from ..LibException import DependencyException


class DependencyFactory:

    _dependency_types = [GetDependency,
                         SetDependency,
                         SwitchDependency]
    _dependency_types_map = {dependency_type.tag: dependency_type for dependency_type in _dependency_types}

    @classmethod
    def create_dependency(cls, dependency_type: str, properties, owner_component, duplicate=False) -> Dependency:
        if dependency_type not in cls._dependency_types_map:
            raise DependencyException(f"Dependency '{dependency_type}' is not supported",
                                      owner_component=owner_component)
        return cls._dependency_types_map[dependency_type](properties, owner_component, duplicate)

