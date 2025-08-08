#!/usr/bin/env python
#-------------------------------------------------------------------------------------------------
# INTEL CONFIDENTIAL
# Copyright 2015 Intel Corporation All Rights Reserved.

# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers or licensors.
# Title to the Material remains with Intel Corporation or its suppliers and licensors.
# The Material may contain trade secrets and proprietary and confidential information of
# Intel Corporation and its suppliers and licensors, and is protected by worldwide copyright
# and trade secret laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed, or disclosed
# in any way without Intels prior express written permission.
# No license under any patent, copyright, trade secret or other intellectual property right
# is granted to or conferred upon you by disclosure or delivery of the Materials, either expressly,
# by implication, inducement, estoppel or otherwise. Any license under such intellectual
# property rights must be express and approved by Intel in writing.

# Unless otherwise agreed by Intel in writing, you may not remove or alter this notice or
# any other notice embedded in Materials by Intel or Intels suppliers or licensors in any way.
#-------------------------------------------------------------------------------------------------
# Name:        <setITPManualScan.py>
#
# Purpose:     Automation script to call klaxon for project specific
#
# Author:      Scott Smith
#
# Created:     01/07/2016
#-------------------------------------------------------------------------------------------------
############################################################################
# $
############################################################################

import sys, argparse
import common.baseaccess as baseaccess

from common import toolbox
_testName = "setITPManualScan"
logfile = _testName + ".log"
_log = toolbox.getLogger(logfile)
_log.setFile(logfile, overwrite=True)
_log.setConsoleLevel("RESULT")
_log.setFileLevel("DEBUGALL")

if baseaccess.getaccess()=="itpii":
    import itpii
    itp = itpii.baseaccess()

def SetItpManualscans():
    """
    This module SETS the ITP control variable, manualscans, to 1
    It returns an error if unsuccessful
    """
    try:
        itp.cv.manualscans=1
    except Exception, e:
        _log.error("Setting ITP CV manualscans to '1' failed. %s" %e)
        return 1
    return 0


def ClearItpManualscans():
    """
    This module CLEARS the ITP control variable, manualscans
    It returns an error if unsuccessful
    """
    try:
        itp.cv.manualscans=0
    except Exception, e:
        _log.error("Setting ITP CV manualscans to '0' failed.")
        _log.error("This is REALLY BAD, as C-states will not work until you fix this.")
        _log.error("Please make sure to run itp.cv.manualscans=0 manually before using this system further!!")
        _log.error("ITP error text: %s" %e)
        return 1
    return 0

def main():
    parser = argparse.ArgumentParser(description='Process argument to if we are setting or clearing ITPManualScan')
    parser.add_argument("--clear", action="store_true", default=False)
    parser.add_argument("--set",   action="store_true", default=False)
    args = parser.parse_args()
    errcnt = 0

    if (args.set and args.clear): # can't set and clear at the same time
        _log.error("You can't set and clear ITP Manual Scans at the same time.")  
        return 1

    if args.set:
        SetItpManualscans()
        return 0

    if args.clear:
        ClearItpManualscans()
        return 0

    # If we didn't specify set or clear, then there's something wrong.
    _log.error("You didn't specify if you wanted to set it or clear it.")
    return 1

if __name__ == '__main__':
    sys.exit(main())