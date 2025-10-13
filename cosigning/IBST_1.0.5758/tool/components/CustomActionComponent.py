#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTEL CONFIDENTIAL
Copyright 2020-2022 Intel Corporation.
This software and the related documents are Intel copyrighted materials, and
your use of them is governed by the express license under which they were
provided to you (License).Unless the License provides otherwise, you may not
use, modify, copy, publish, distribute, disclose or transmit this software or
the related documents without Intel's prior written permission.

This software and the related documents are provided as is, with no express or
implied warranties, other than those that are expressly stated in the License.
"""
from enum import Enum

from ..Converter import Converter
from ..components.IComponent import IComponent
from ..LibException import ComponentException
from ..components.function.SignFunction import SignFunction


class CustomActionComponent(IComponent):
    OfflineSigning = 'offline_signing'
    SupportedActions = [OfflineSigning]
    nodeName = "custom_actions"
    typeTag = "action_type"
    activationTag = "activation"

    class ActionType(Enum):
        Callback = 'callback'
        DirectCall = 'direct call'

    class ActivationType(Enum):
        OnChange = 'on change'

    def __init__(self, xml_node, **kwargs):
        self.type = self._parse_type_attribute(xml_node)
        self.activation = self._parse_activation_type(xml_node)
        self.enabled = True
        super().__init__(xml_node, **kwargs)

    def _parse_type_attribute(self, xml_node):
        if self.typeTag in xml_node.attrib:
            if not xml_node.attrib[self.typeTag] in [action.value for action in CustomActionComponent.ActionType]:
                raise ComponentException(f"Unrecognized action type.\n'{xml_node.attrib[self.typeTag]}'"
                                         f" is not supported action for custom actions.")

            return xml_node.attrib[self.typeTag]

    def _parse_activation_type(self, xml_node):
        if self.activationTag in xml_node.attrib:
            if not xml_node.attrib[self.activationTag] in \
                   [activation.value for activation in CustomActionComponent.ActivationType]:
                raise ComponentException(f"Unrecognized activation type.\n'{xml_node.attrib[self.activationTag]}'"
                                         f" is not supported activation for custom actions.")

            return xml_node.attrib[self.activationTag]

    @staticmethod
    def is_supported(action):
        return action.name in CustomActionComponent.SupportedActions

    @staticmethod
    def is_callback(action):
        return action.type == CustomActionComponent.ActionType.Callback.value


class ICallbackData:
    def __init__(self, cont_name: str, plugin_name: str, action: CustomActionComponent):
        self.container_name = cont_name
        self.plugin_name = plugin_name
        self.action_label = action.label
        self.action_name = action.name


class OfflineSigningSettings:
    def __init__(self, sign_function: SignFunction):
        self.sign_function: SignFunction = sign_function


class OfflineSigningDetails:
    def __init__(self, settings: OfflineSigningSettings, buffer: bytes):
        self.sha_value = Converter.bytes_to_string(settings.sign_function.get_sha(buffer))
        self.sha_type = settings.sign_function.sha_type.name.upper()
        self.key_path = settings.sign_function.key.value
        self.key_type = settings.sign_function.key.formatted_key_type() + ":" + settings.sign_function.padding_scheme.name.upper()
        self.component_name = settings.sign_function.component_name
        self.signing_setting_name = settings.sign_function.name
        self.signature_file_setting_name = settings.sign_function.signature_file.name

    @staticmethod
    def all_required_settings_are_set(settings: OfflineSigningSettings):
        return settings and settings.sign_function and settings.sign_function.offline_signing and \
               settings.sign_function.signature_not_given() and settings.sign_function.sha_type and \
               settings.sign_function.sha_type.value


class OfflineSigningCallbackData(ICallbackData):
    def __init__(self, action: CustomActionComponent, container_name: str, plugin_name: str,
                 details: [OfflineSigningDetails]):
        super().__init__(container_name, plugin_name, action)
        self.signing_details = details
