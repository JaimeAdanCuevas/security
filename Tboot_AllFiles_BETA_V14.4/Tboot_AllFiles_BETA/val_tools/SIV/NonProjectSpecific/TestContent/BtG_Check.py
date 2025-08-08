#!/usr/bin/python
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corp-
# oration or its suppliers and licensors. The Material may contain trade
# secrets and proprietary and confidential information of Intel Corpor-
# ation and its suppliers and licensors, and is protected by worldwide
# copyright and trade secret laws and treaty provisions. No part of the
# Material may be used, copied, reproduced, modified, published, uploaded,
# posted, transmitted, distributed, or disclosed in any way without
# Intel's prior express written permission.cvcv#
# No license under any patent, copyright, trade secret or other intellect-
# ual property right is granted to or conferred upon you by disclosure or
# delivery of the Materials, either expressly, by implication, inducement,
# estoppel or otherwise. Any license under such intellectual property
# rights must be express and approved by Intel in writing.
##############################################################################


"""
    INTEL CONFIDENTIAL - DO NOT RE-DISTRUBUTE
    Copyright 2010 Intel Corporation All Rights Reserved.

    Author: Vanila Reddy
    e-mail: vanila.reddy@intel.com
    Date:   Nov 2016

    Description: Prints and checks uCode value via ITP 
"""


import StringIO
import os
import sys
import time


if r'C:\PythonSV' not in sys.path: sys.path.append(r"C:\PythonSV")
True = 0
False = 1

import common
import common.toolbox
import itpii
"""if 'itpii' not in sys.modules.keys():
    imp.find_module("itpii")"""

from components.corecode import bits
from itpii.datatypes import BitData
MSR_dis = False
itp = itpii.baseaccess()
"""import sys
import common.baseaccess as ba
base = ba.getglobalbase()
itp = base.getapi()"""

def Setup():
    global MSR_dis
    return MSR_dis
    
def Read():
    global MSR_dis
    itp.halt()
    itp.log(r"C:\Temp\BtG_msr_value.log")
    itp.msr(0x13a)
    itp.nolog
    itp.go()
    msr1testfile = open(r"C:\Temp\BtG_msr_value.log")
    msr1testfile.readline()
    line = msr1testfile.readline()
    line = line.strip()
    array1 = line.split(" ")
    print array1
    msr1testfile.close()
    value1 = long(array1[2],16)
    if (value1 == long("0x0000000400000000",16)):
        MSR_dis = True
        print "BootGuard Profile 0 Enabled"
        return True
    elif (value1 == long("0x000000070000006D",16)):
        print "BootGuard Profile 3 Enabled"
        return True
    elif (value1 == long("0x0000000700000051",16)):
        print "BootGuard Profile 4 Enabled"
        return True
    elif (value1 == long("0x000000070000007D",16)):
        print "BootGuard Profile 5 Enabled"
        return True
    else:
        print "Failed to read msr 0x13a" 
        return False
		

def main():
    time.sleep(10)
    ret = Read()
    print(ret)
    sys.exit(ret)

if __name__ == "__main__":
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully
