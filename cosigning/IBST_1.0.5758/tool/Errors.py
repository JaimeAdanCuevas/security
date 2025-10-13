"""
INTEL CONFIDENTIAL
Copyright 2022-2024 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""


class ErrorMessage:
    """Single error message."""
    def __init__(self, message: str, code: int, cli: bool, gui: bool):
        self.message: str = message
        self.code: int = code
        self.cli: bool = cli
        self.gui: bool = gui


class MetaErrors(type):
    """Meta class for Errors. Enables us to iterate over class, without instance of said class."""
    def __iter__(cls):
        """Returns iterator with all ErrorMessages defined in the base class - Errors."""
        return (v for v in vars(cls).values() if isinstance(v, ErrorMessage))


class Errors(metaclass=MetaErrors):
    """Static class storing all ErrorMessages."""
    # UniqueKey
    wrong_container_version = ErrorMessage("Failed to parse version: '{version}' for {container_name}", 101, True, True)
    wrong_container_name = ErrorMessage("Internal error: failed to convert unique name: {container_name}",
                                        102, True, True)

    # Dependency
    bit_range_to_settings = ErrorMessage("Bit range can be applied only to numbers", 801, True, True)

    @classmethod
    def print_error_messages(cls):
        """
        Method only for debug purposes. Allow the developer to print the error messages (should not be exposed to
        customers).
        """
        print("Error code; Message; Shown in CLI; Shown in GUI;")
        for error in cls:
            print(f"{error.code}; {error.message}; {error.cli}; {error.gui}")
