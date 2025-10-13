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
import sys
from contextlib import contextmanager
from enum import Enum
from importlib.util import find_spec


from .LibConfig import LibConfig


class ColorPrint:

    CS = '\x1b['
    Reset = f'{CS}0m'
    can_import_colorama = False
    show_warnings = True
    buffer = []
    is_gui = True

    class Colors(Enum):
        black = 0
        red = 1
        green = 2
        yellow = 3
        blue = 4
        magenta = 5
        cyan = 6
        white = 7

    class MsgType:
        success = "success_msg"
        error = "error_msg"
        debug = "debug_msg"
        warn = "warn_msg"
        info = "info_msg"

    # gui_visible argument of printing functions is necessary for this decorator
    def save_to_buffer(msg_type, gui=is_gui, gui_visible_default=False):
        def func_wrap(func):
            def wrapper(cls, msg, end='\n', gui_visible=gui_visible_default):
                func(cls, msg, end)
                if gui_visible and ColorPrint.is_gui:
                    cls.buffer.append((msg_type, msg))
            return wrapper
        return func_wrap

    @classmethod
    def read_buffer(cls):
        temp_buff = []
        temp_buff.extend(cls.buffer)
        cls.buffer = []
        return temp_buff

    @staticmethod
    def setup_colorama():
        if find_spec('colorama'):
            import colorama
            colorama.init()
            ColorPrint.can_import_colorama = True

    @classmethod
    def _wrap_message(cls, message, color, bright, end):
        offset = 90 if bright else 30
        return f'{cls.CS}{offset + color.value}m{message}{cls.Reset}{end}' if cls.can_import_colorama else f'{message}{end}'

    @classmethod
    @save_to_buffer(MsgType.info)
    def info(cls, message, end='\n', gui_visible=False):
        sys.stdout.write(cls._wrap_message(message, cls.Colors.white, False, end))

    @classmethod
    @save_to_buffer(MsgType.success)
    def success(cls, message, end='\n', gui_visible=False):
        sys.stdout.write(cls._wrap_message(message, cls.Colors.green, True, end))

    @classmethod
    @save_to_buffer(MsgType.error, gui_visible_default=True)
    def error(cls, message, end='\n', gui_visible=True):
        sys.stdout.write(cls._wrap_message(message, cls.Colors.red, True, end))

    @classmethod
    @save_to_buffer(MsgType.debug)
    def debug(cls, message, end='\n', gui_visible=False):
        if LibConfig.is_verbose:
            sys.stdout.write(cls._wrap_message(message, cls.Colors.cyan, False, end))

    @classmethod
    @save_to_buffer(MsgType.warn, gui_visible_default=True)
    def warning(cls, message, end='\n', gui_visible=True):
        if ColorPrint.show_warnings:
            sys.stdout.write(cls._wrap_message(message, cls.Colors.yellow, True, end))

    @staticmethod
    @contextmanager
    def no_warnings():
        start_value = ColorPrint.show_warnings
        ColorPrint.show_warnings = False
        yield
        ColorPrint.show_warnings = start_value
