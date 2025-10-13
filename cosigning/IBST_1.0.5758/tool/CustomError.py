#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2021-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
from enum import Enum

from .ColorPrint import log
from .LibConfig import LibConfig


class Severity(Enum):
    ERROR = 'Error'
    WARNING = 'Warning'
    GUI_ONLY_WARNING = 'Gui_Warning'
    BUILD_ONLY_ERROR = 'Build_Error'


class CustomErrorException(Exception):
    def __init__(self, message, custom_error):
        super().__init__(message)
        self.message = message
        self.custom_error = custom_error

    def __str__(self):
        return self.message


class CustomError:
    messageTag = 'message'
    severityTag = 'severity'
    """
    Handles custom errors defined in 'validate' attribute in JSON format.
    """
    def __init__(self, component):
        """
        Initializes CustomError members with late verification on 'self.validate()'.
        :param component: instance of IComponent class.
        """
        self.component = component
        validate_formula_json = component.validate_formula_json
        self.calculate_formula = validate_formula_json['calculate']
        self.build_error = False
        self.severity = None

        if self.messageTag not in validate_formula_json:
            self.message = f"Validation formula for '{component.name}' failed due to:\n{self.calculate_formula}"
        else:
            self.message = validate_formula_json[self.messageTag].replace("‘", "'")

        if self.severityTag not in validate_formula_json:
            self.severity = Severity.ERROR.value
        elif isinstance(validate_formula_json[self.severityTag], str) and \
                validate_formula_json[self.severityTag] in [item.value for item in Severity]:
            self.severity = validate_formula_json[self.severityTag]
            self.build_error = Severity.BUILD_ONLY_ERROR.value == validate_formula_json[self.severityTag]
        elif isinstance(validate_formula_json[self.severityTag], list):
            self._assign_severity_by_priority(validate_formula_json[self.severityTag])
            if Severity.BUILD_ONLY_ERROR.value in validate_formula_json[self.severityTag]:
                self.build_error = True
        else:
            self.severity = Severity.ERROR.value

    def _assign_severity_by_priority(self, severities: list):
        if Severity.ERROR.value in severities:
            self.severity = Severity.ERROR.value
        elif Severity.WARNING.value in severities:
            self.severity = Severity.WARNING.value
        elif Severity.GUI_ONLY_WARNING.value in severities:
            self.severity = Severity.GUI_ONLY_WARNING.value

    def occurs(self, build_check=False):
        """
        Verify if custom error occurs.
        :param build_check: Check occurred during build
        :returns True if validation formula from json evaluates to True and should be considered
        """
        custom_error_should_be_considered = (self.severity != Severity.GUI_ONLY_WARNING.value or LibConfig.isGui) and \
                                            self.severity is not None
        custom_error_on_build = build_check and self.build_error
        custom_error_occurs = not self.component.calculate_value(self.calculate_formula) and \
            (custom_error_should_be_considered or custom_error_on_build)
        if custom_error_occurs:
            self.message += f'\nIn: {self.component.name}, value: {str(self.component.user_set_value)}'
            if self.severity == Severity.ERROR.value or custom_error_on_build:
                self.severity = Severity.ERROR.value
                raise CustomErrorException(self.message, self)
            if not custom_error_on_build and self.severity == Severity.BUILD_ONLY_ERROR.value:
                return False
            log().warning("Warning for: " + self.component.name + ". " + self.message)
        return custom_error_occurs
