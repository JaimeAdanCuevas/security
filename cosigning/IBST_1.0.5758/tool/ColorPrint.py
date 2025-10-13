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
import os
import shutil
import sys
import threading

from copy import deepcopy
from enum import Enum
from importlib.util import find_spec
from typing import Dict
from datetime import datetime

from .LibConfig import LibConfig
from .LibException import WrongTypeException


class ColorPrint:
    """This is a base logger class. Usage of ColorPrint directly is deprecated, use log() function instead."""
    CS = '\x1b['
    Reset = f'{CS}0m'
    can_import_colorama = False
    buffer = []
    log_buffer = []
    buffer_lock = threading.RLock()
    log_buffer_lock = threading.RLock()
    is_gui = True
    log_path = ''
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB

    class Colors(Enum):
        BLACK = 0
        RED = 1
        GREEN = 2
        YELLOW = 3
        BLUE = 4
        MAGENTA = 5
        CYAN = 6
        WHITE = 7

    class MsgType:
        success = "success_msg"
        error = "error_msg"
        debug = "debug_msg"
        warn = "warn_msg"
        info = "info_msg"

    gui_visibility = {
        MsgType.success: False,
        MsgType.error: True,
        MsgType.debug: False,
        MsgType.warn: True,
        MsgType.info: False
    }

    should_popup = {
        MsgType.success: True,
        MsgType.error: True,
        MsgType.debug: False,
        MsgType.warn: True,
        MsgType.info: False
    }

    @classmethod
    def set_log_path(cls, path):
        """
        Sets path for log file. If the same already exists and it's size exceeds the limit:
        - renames previous one by adding timestamp
        - create new one in place

        :param path: path to be set
        """
        if cls._log_already_exists_and_exceeds_size_limit(path):
            cls._rename_old_log(path)
        cls.log_path = path

    @classmethod
    def _log_already_exists_and_exceeds_size_limit(cls, path):
        return os.path.exists(path) and os.path.getsize(path) > cls.MAX_LOG_SIZE

    @classmethod
    def _rename_old_log(cls, path):
        from .utils import get_file_name_no_ext  # pylint: disable=import-outside-toplevel
        log_name = get_file_name_no_ext(path)
        timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        new_log_name = f"{log_name}_{timestamp}.log"
        log_dir = os.path.dirname(path)
        destination = os.path.join(log_dir, new_log_name)
        shutil.move(path, destination)

    def save_to_buffer(msg_type):  # pylint: disable=no-self-argument
        from_gui_default = False
        gui_visible_default = None
        popup_default = None
        # Only system messages will be gathered by ping and redirect_logs
        system_default = False

        def func_wrap(func):
            def wrapper(cls, msg, end='\n', from_gui=from_gui_default, gui_visible=gui_visible_default,
                        popup=popup_default, system=system_default):
                gui_visible = cls.get_default_gui_visibility(msg_type) if gui_visible is None else gui_visible
                popup = cls.get_default_should_popup(msg_type) if popup is None else popup
                func(cls, msg, end, from_gui)
                if gui_visible and ColorPrint.is_gui:
                    with cls.buffer_lock:
                        cls.buffer.append((msg_type, msg, popup, system))

            return wrapper
        return func_wrap

    def save_to_log_buffer(with_timestamp=False, no_new_lines=False):  # pylint: disable=no-self-argument
        def func_wrap(func):
            def wrapper(cls, msg, end='\n', from_gui=False):
                func(cls, msg, end, from_gui)
                if LibConfig.saveLog:
                    with cls.log_buffer_lock:
                        msg = '[GUI] ' + str(msg) if from_gui else str(msg)
                        if no_new_lines:
                            msg = msg.lstrip().rstrip()
                        if with_timestamp:
                            msg = cls.get_timestamped_message(msg)
                        cls.log_buffer.append(msg + end)

            return wrapper
        return func_wrap

    @classmethod
    def try_save_to_log(cls):
        """
        Tries to save log buffered messages to log file. If log file is inaccessible, prints the warning message.
        :return: True if succeed to save log.
        """
        if LibConfig.saveLog:
            from .FileManager import FileManager  # pylint: disable=import-outside-toplevel
            with cls.log_buffer_lock:
                try:
                    if not os.path.exists(os.path.dirname(cls.log_path)):
                        os.makedirs(os.path.dirname(cls.log_path), exist_ok=True)
                    FileManager.save_file(cls.log_path, ''.join(cls.log_buffer), 'a')
                    return True
                except Exception as ex:
                    # Disable writing to file when there was an exception. This prevents displaying infinite amount
                    # of errors to user in GUI. Fit will continue working without writing logs to file.
                    LibConfig.saveLog = False
                    ColorPrint.warning(f"{str(ex)} Logs will be only shown in console.", gui_visible=True, system=True)
                    return False
                finally:
                    cls.log_buffer.clear()
        else:
            return False

    @classmethod
    def read_buffer(cls, system_only):
        temp_buff = []
        with cls.buffer_lock:
            if system_only:
                temp_buff.extend([msg for msg in cls.buffer if msg[3]])
                cls.buffer = [msg for msg in cls.buffer if not msg[3]]
            else:
                temp_buff.extend(cls.buffer)
                cls.buffer.clear()
        return temp_buff

    @staticmethod
    def setup_colorama():
        if find_spec('colorama'):
            import colorama  # pylint: disable=import-outside-toplevel
            colorama.init()
            ColorPrint.can_import_colorama = True

    @classmethod
    def _wrap_message(cls, message, color, bright, end):
        offset = 90 if bright else 30
        return f'{cls.CS}{offset + color.value}m{message}{cls.Reset}{end}' if cls.can_import_colorama \
            else f'{message}{end}'

    @classmethod
    def get_default_gui_visibility(cls, msg_type):
        return cls.gui_visibility[msg_type]

    @classmethod
    def get_default_should_popup(cls, msg_type):
        return cls.should_popup[msg_type]

    @classmethod
    def get_timestamped_message(cls, message):
        return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]}] {message}"

    # pylint: disable=unused-argument,too-many-function-args
    @classmethod
    @save_to_buffer(MsgType.info)
    @save_to_log_buffer()
    def info(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes info message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        sys.stdout.write(cls._wrap_message(message, cls.Colors.WHITE, False, end))

    @classmethod
    @save_to_buffer(MsgType.success)
    @save_to_log_buffer()
    def success(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes success message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        sys.stdout.write(cls._wrap_message(message, cls.Colors.GREEN, True, end))

    @classmethod
    @save_to_buffer(MsgType.error)
    @save_to_log_buffer()
    def error(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes error message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        sys.stdout.write(cls._wrap_message(message, cls.Colors.RED, True, end))

    @classmethod
    @save_to_buffer(MsgType.debug)
    @save_to_log_buffer()
    def debug(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes debug message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        if LibConfig.isVerbose:
            sys.stdout.write(cls._wrap_message(message, cls.Colors.CYAN, False, end))

    @classmethod
    @save_to_buffer(MsgType.warn)
    @save_to_log_buffer()
    def warning(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes warning message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        sys.stdout.write(cls._wrap_message(message, cls.Colors.YELLOW, True, end))

    @classmethod
    def txt_only(cls, message, message_type):
        """
        Saves message to the log without doing any additional actions. To avoid changing the decorator using info type.
        """
        @cls.save_to_log_buffer()
        def _txt_only(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
            pass
        _txt_only(cls, message)
    # pylint: enable=unused-argument,too-many-function-args

    @classmethod
    def get_method_by_message_type(cls, message_type: str):
        """
        Fabrication method return the method for
        :param message_type: enum MsgType
        :return: proper logging method per message type
        :raises: library.exceptions.WrongTypeException() in case wrong message type was provided
        """
        if message_type == cls.MsgType.info:
            return cls.info
        if message_type == cls.MsgType.debug:
            return cls.debug
        if message_type == cls.MsgType.error:
            return cls.error
        if message_type == cls.MsgType.warn:
            return cls.warning
        if message_type == cls.MsgType.success:
            return cls.success
        raise WrongTypeException(f'Invalid message type detected. Expecting member of {cls.MsgType}'
                                 f' Got: {message_type}')


class MergeColorPrint(ColorPrint):
    """
    Used for logging during the XML merger process
    """
    log_path = ''
    buffer = []
    log_buffer = []
    gui_visibility = {
        ColorPrint.MsgType.success: True,
        ColorPrint.MsgType.error: True,
        ColorPrint.MsgType.debug: False,
        ColorPrint.MsgType.warn: False,
        ColorPrint.MsgType.info: False
    }


class DecomposeColorPrint(ColorPrint):
    """
    Used for logging during the decomposition process
    """
    log_path = ''
    buffer = []
    log_buffer = []
    gui_visibility = {
        ColorPrint.MsgType.success: True,
        ColorPrint.MsgType.error: True,
        ColorPrint.MsgType.warn: True,
        ColorPrint.MsgType.debug: False,
        ColorPrint.MsgType.info: False
    }


class SecurityColorPrint(ColorPrint):
    """
    Used for logging security events. These consist of:
    - Access list checks.
    - Issues with communication between server and GUI.
    - Sharing of secrets between server and GUI.
    - Any other event that can be considered a security issue.
    """
    log_path = ''
    buffer = []
    log_buffer = []

    @classmethod
    @ColorPrint.save_to_buffer(ColorPrint.MsgType.info)
    @ColorPrint.save_to_log_buffer(True, True)
    def info(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes info message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        ColorPrint.info(message, end, from_gui, gui_visible, popup)

    @classmethod
    @ColorPrint.save_to_buffer(ColorPrint.MsgType.success)
    @ColorPrint.save_to_log_buffer(True, True)
    def success(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes success message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        ColorPrint.success(message, end, from_gui, gui_visible, popup)

    @classmethod
    @ColorPrint.save_to_buffer(ColorPrint.MsgType.error)
    @ColorPrint.save_to_log_buffer(True, True)
    def error(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes error message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        ColorPrint.error(message, end, from_gui, gui_visible, popup)

    @classmethod
    @ColorPrint.save_to_buffer(ColorPrint.MsgType.debug)
    @ColorPrint.save_to_log_buffer(True, True)
    def debug(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes debug message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        ColorPrint.debug(message, end, from_gui, gui_visible, popup)

    @classmethod
    @ColorPrint.save_to_buffer(ColorPrint.MsgType.warn)
    @ColorPrint.save_to_log_buffer(True, True)
    def warning(cls, message, end='\n', from_gui=False, gui_visible=None, popup=True, system=False):
        """
        Writes warning message to standard output stream.
        :param message: message to write.
        :param end: message suffix.
        :param from_gui: indicates if it's a message from GUI.
        :param gui_visible: indicates if the message should be visible in GUI.
        :param popup: indicates if the message should pop up in GUI.
        :param system: indicates if the message should be instantly shown in GUI (gathered by ping).
        :return: copy of the buffer.
        """
        ColorPrint.warning(message, end, from_gui, gui_visible, popup)


def log():
    """
    Gets appropriate ColorPrint class depending on current action.
    """
    if LibConfig.isDecompose:
        return DecomposeColorPrint
    if LibConfig.isMerge:
        return MergeColorPrint
    if LibConfig.isSecurity:
        return SecurityColorPrint
    return ColorPrint


def save_to_all_logs(message, message_type=ColorPrint.MsgType.info):
    """
    Saves a given message to all supported logs. Prints the message only once.
    :param message: message to be saved
    :param message_type: message type of the message to be saved
    """
    ColorPrint.get_method_by_message_type(message_type)(message)
    if LibConfig.toolType == LibConfig.ToolType.FIT:
        MergeColorPrint.txt_only(message, message_type)
        DecomposeColorPrint.txt_only(message, message_type)
        SecurityColorPrint.txt_only(message, message_type)


def save_logs():
    """
    Saves all logs for each ColorPrint class.
    """
    ColorPrint.try_save_to_log()
    DecomposeColorPrint.try_save_to_log()
    MergeColorPrint.try_save_to_log()
    SecurityColorPrint.try_save_to_log()


def read_gui_buffer(system_only: bool):
    """
    Reads all log buffers from each ColorPrint class.
    :param system_only: if set, only system messages will be read.
    """
    buffer = []
    buffer.extend(ColorPrint.read_buffer(system_only))
    buffer.extend(MergeColorPrint.read_buffer(system_only))
    buffer.extend(DecomposeColorPrint.read_buffer(system_only))

    return buffer


def log_security_warning(message: str):
    """
    Logs a warning using SecurityContextManager.

    :param message: message to be logged
    """
    from app.utils import SecurityContextManager  # pylint: disable=import-outside-toplevel
    with SecurityContextManager():
        log().warning(message)


def override_should_popup(should_popup_overrides: Dict[ColorPrint.MsgType, bool]):
    """
    Decorator used to override ColorPrint.should_popup, values of this dict will be reset after function execution
    :param should_popup_overrides: overrides for should_popup dictionary
    :return: decorated function
    """
    def func_wrap(func):
        def wrapper(*args, **kwargs):
            should_popup_backup = deepcopy(ColorPrint.should_popup)
            ColorPrint.should_popup.update(should_popup_overrides)
            ret_value = func(*args, **kwargs)
            ColorPrint.should_popup = should_popup_backup
            return ret_value
        return wrapper
    return func_wrap
