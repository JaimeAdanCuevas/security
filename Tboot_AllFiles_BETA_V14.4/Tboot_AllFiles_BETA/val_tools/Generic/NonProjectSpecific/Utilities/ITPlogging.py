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
# Name:        <ITPlogging.py>
#
# Purpose:     To turn on/off ITP logging for Automation
#
# Author:      Ankit Agiwal
#
# Created:     08/12/2016
#-------------------------------------------------------------------------------------------------
############################################################################
# $
############################################################################

import sys, argparse
import traceback
import common.baseaccess as baseaccess

from common import toolbox
_testName = "itplogging_debug"
logfile = _testName + ".log"
_log = toolbox.getLogger(logfile)
_log.setFile(logfile, overwrite=True)
_log.setConsoleLevel("RESULT")
_log.setFileLevel("DEBUGALL")

def main():
    parser = argparse.ArgumentParser(description='Process argument to Turn ON and OFF the ITP logging')
    parser.add_argument("--on", action="store_true", default=False)
    parser.add_argument("--off", action="store_true", default=False)
    args = parser.parse_args()
    errcnt = 0
    _log.result("Starting the ITPlogging script")
    
    _log.result("Loading Masterframe...")
    import itpii
    itp = itpii.baseaccess()
    
    try:        
        if args.on==True:
            _log.result("Enabling ITP Standard Logging...")
            itp.daldebugloggerlevel("standard")
    except:
        return 1
    
    try:
        if args.off==True:
            _log.result("Saving the ITP Standard Logging...")
            itp.loggerarchive()
            _log.result("Clearing individual ITP Standard Logging as they are saved to zip file...")
            itp.loggerclear()
            _log.result("Disabling ITP Standard Logging...")
            itp.loggeroff()
    except:
        return 1
    
    return 0
    
if __name__ == '__main__':
    sys.exit(main())