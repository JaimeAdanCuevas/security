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

# pylint: disable=pointless-string-statement
'''
This package consists of the Components that repentants the xml nodes in the xml layout of the container

E. G.

<container>
    <layout>
      <number name="setting1" value="0x400000" />
      <number name="setting2" value="0x180000" /> 
    </layout> 
</container

is mapped to the 

obj BinGenerator:
    children:
        obj NumberComponent setting1
        obj NumberComponent setting2
        
and binary can be created by calling build method on BinGenerator

'''
