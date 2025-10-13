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
from ...LibException import ComponentException
from ...components.function.IFunction import IFunction
from ...cryptography_helpers import get_montgomery_precomputes
from ...structures import ByteOrder


class ModulusFunction(IFunction):
    """
    Function responsible for calculating private moduluses n2 and n3, based on public modulus.
    """

    keySizeTag = "key_size"
    publicModulusTag = "public_modulus"
    key_size = None
    public_modulus = None
    _size = None
    _key_size_formula = None

    def __init__(self, xml_node, **kwargs):
        super().__init__(xml_node, **kwargs)
        self.align_byte = self.AlignByte.Byte00

    def _parse_children(self, xml_node, **kwargs):
        super()._parse_children(xml_node, **kwargs)
        self._key_size_formula = self.parse_extra_node(xml_node, self.keySizeTag)
        self.public_modulus_formula = self.parse_extra_node(xml_node, self.publicModulusTag)

    @property
    def size(self):
        if self._size is not None:
            return self._size

        if self.key_size is not None:
            self._size = self.key_size * 2
            return self._size

        if self._key_size_formula is not None:
            self.key_size = self.calculate_value(formula=self._key_size_formula)
            self._size = self.key_size * 2
            return self._size

        return None

    @size.setter
    def size(self, value):
        self._size = value

    def _build(self, buffer):
        super()._build(buffer)

        self.key_size = self.calculate_value(formula=self._key_size_formula)
        self.public_modulus = int.from_bytes(self.calculate_value(formula=self.public_modulus_formula),
                                             byteorder=ByteOrder.LITTLE.value)

        _, n2, n3 = get_montgomery_precomputes(self.key_size * 8, self.public_modulus)
        n2_bytes = n2.to_bytes(self.key_size, byteorder=ByteOrder.LITTLE.value)
        n3_bytes = n3.to_bytes(self.key_size, byteorder=ByteOrder.LITTLE.value)

        modulus_bytes = bytearray()
        modulus_bytes.extend(n2_bytes[::] + n3_bytes[::])

        self.set_value(modulus_bytes)
