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
from .LibException import LibException


def get_multiplicative_modular_inverse(a: int, b: int):
    """
    Get multiplicative modular inverse
    :param a: Input number 1
    :param b: Input number 2
    :return: Multiplicative modular inverse
    :raises: LibException if inverse does not exist for the input pair
    """
    try:
        from sympy import mod_inverse
        return mod_inverse(a, b)
    except ValueError as e:
        raise LibException(f"Multiplicative modular inverse does not exist for {a} and {b}. "
                           f"Please verify that the key you provided is a valid key.") from e


def get_montgomery_precomputes(key_size: int, public_key_modulus: int):
    """
    Get precomputes for Montgomery reduction
    :param key_size: Key size in bits
    :param public_key_modulus: Public key modulus
    :return: Tuple of (R, modulus N2, modulus N3)
    """

    r = 2 ** key_size
    n_prime = (r * get_multiplicative_modular_inverse(r, public_key_modulus) - 1) // public_key_modulus
    n_double_prime = (r ** 2) % public_key_modulus

    return r, n_prime, n_double_prime
