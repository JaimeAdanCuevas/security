#!/usr/bin/env python
#+----------------------------------------------------------------------------+
#| INTEL CONFIDENTIAL
#| Copyright 2014 Intel Corporation All Rights Reserved.
#| 
#| The source code contained or described herein and all documents related
#| to the source code ("Material") are owned by Intel Corporation or its
#| suppliers or licensors. Title to the Material remains with Intel Corp-
#| oration or its suppliers and licensors. The Material may contain trade
#| secrets and proprietary and confidential information of Intel Corpor-
#| ation and its suppliers and licensors, and is protected by worldwide
#| copyright and trade secret laws and treaty provisions. No part of the
#| Material may be used, copied, reproduced, modified, published, uploaded,
#| posted, transmitted, distributed, or disclosed in any way without
#| Intel's prior express written permission.
#| 
#| No license under any patent, copyright, trade secret or other intellect-
#| ual property right is granted to or conferred upon you by disclosure or
#| delivery of the Materials, either expressly, by implication, inducement,
#| estoppel or otherwise. Any license under such intellectual property
#| rights must be express and approved by Intel in writing.
#+----------------------------------------------------------------------------+
#| $Id: DisableRecovery.py 62 2014-11-21 22:46:38Z amr\egross $
#| $Date: 2014-11-21 14:46:38 -0800 (Fri, 21 Nov 2014) $
#| $Author: amr\egross $
#| $Revision: 62 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    This script Disable the recovery of the system.
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
import subprocess   as _subprocess
import shlex        as _shlex
from optparse import OptionParser

## Global Variables/Constants
bDEBUG                  = 0
nOutputWidth            = 80
__version__             = "$Rev: 62 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDEBUG): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "../../../../Generic/NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
if (bDEBUG): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDEBUG):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

lLogger                 = _ValToolsUtilities.setupLogger(bDEBUG, sLogfileName)

#+----------------------------------------------------------------------------+
#    XX     XX  XXX      XXXXX  XX   XXXX
#     X     X     X        X     X     X
#     XX   XX    X X       X     XX    X
#     XX   XX    X X       X     X X   X
#     X X X X   X   X      X     X X   X
#     X X X X   X   X      X     X  X  X
#     X  X  X   XXXXX      X     X   X X
#     X  X  X  X     X     X     X   X X
#     X     X  X     X     X     X    XX
#    XXX   XXXXXX   XXX  XXXXX  XXXX   X
#+----------------------------------------------------------------------------+
def main():
    #  Variable definitions
    bErrorsOccurred         = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __version__)

    
    #  Explain what we're doing and why
    lLogger.info("SIV uses bit0 of NVRAM offset 0x71 (BIOS Scratchpad) to indicate to") 
    lLogger.info("    GRUB whether to allow normal trusted boot (value=0) or to force") 
    lLogger.info("    a legacy (untrusted) boot (value=1).") 

    #  System call writing value 0x71 to CMOS register at offset 0x70
    lLogger.info("Setting NVRAM Index by writing value of 0x71 to IO address 0x70") 
    sCommand = "outb 0x70 0x71"
    nCommandRc = _os.system(sCommand)
    
    if (nCommandRc != 0):
        lLogger.error("OS command to write to IO address 0x70 failed.")
        lLogger.error("Command was: '%s'" % sCommand)
        lLogger.error("This is a critical step, so I can't continue...")
        return 0

    #  Read the value from NVRAM by accessing IO address 0x71
    #  Note: this is extra confusing because we're using IO address 0x71
    #  to access NVRAM Index 0x71
    lLogger.info("Reading IO address 0x71 to get the NVRAM data...") 
    sCommand = "inb 0x71"
    sNvramData = "0xDEADBEEF"
    try:
        spIoRead = _subprocess.Popen(_shlex.split(sCommand), stdout=_subprocess.PIPE)
    except:
        lLogger.error("OS command to read to IO address 0x71 failed.")
        lLogger.error("Command was: '%s'" % sCommand)
        lLogger.error("This is a critical step, so I can't continue...")
        return 0
    else:
        sNvramData = spIoRead.stdout.read().rstrip('\n')
        lLogger.info("Successfully read IO address 0x71 and got 0x%08x" % int(sNvramData))
    
    #  Checking the last bit of value at offset 0x71 to determine if
    #  Recovery Mode is currently enabled
    if (int(sNvramData) & (0x01) == 0x01):
        lLogger.info("Bit0 of NVRAM 0x71 is '1', so we'll need to clear it.")
        
        #  Performing bitwise 'and' operation with 0xFFFF_FFFE
        #  to change Bit0 from one to zero
        nNewNvramValue= (int(sNvramData) & 0xFFFFFFFE)
        lLogger.info("Value to be written to NVRAM: 0x%08x" % nNewNvramValue)
    
        #  Writing the new value with last bit changed to zero at address 0x71
        sCommand = "outb 0x71 0x%s" % nNewNvramValue
        nCommandRc = _subprocess.call(_shlex.split(sCommand))
        if (nCommandRc != 0):
            lLogger.error("OS command to write to IO address 0x70 failed.")
            lLogger.error("Command was: '%s'" % sCommand)
            lLogger.error("This is a critical step, so I can't continue...")
            return 0
        else:
            lLogger.info("NVRAM write successful")

        #  Read the value from NVRAM to ensure it actually got written
        lLogger.info("Reading IO address 0x71 to verify the NVRAM data...") 
        sCommand = "inb 0x71"
        sNvramData = "0xDEADBEEF"
        try:
            spIoRead = _subprocess.Popen(_shlex.split(sCommand), stdout=_subprocess.PIPE)
        except:
            lLogger.error("OS command to read to IO address 0x71 failed.")
            lLogger.error("Command was: '%s'" % sCommand)
            lLogger.error("This is a critical step, so I can't continue...")
            return 0
        else:
            sNvramData = spIoRead.stdout.read().rstrip('\n')
            lLogger.info("Successfully read IO address 0x71 and got 0x%08x" % int(sNvramData))

        #  Checking the last bit of value at offset 0x71 to determine if
        #  Recovery Mode is was successfully disabled
        nExpectedValue = 0x0000000  # Expect Bit0 to be zero for Recovery Disabled
        if (int(sNvramData) & (0x00000001) == nExpectedValue):
            lLogger.info("NVRAM data verified as 0x%08x.  Write was successful."
                         % nExpectedValue)
        else:
            lLogger.error("NVRAM data NOT verified.  ")
            lLogger.error("   Read:     0x%08x" % int(sNvramData))
            lLogger.error("   Expected: 0x%08x" % nExpectedValue)
            bErrorsOccurred = True
    
    #  Enters here if the system is already disbaled i.e. Bit0 of 
    #  NVRAM Offset 0x71 is 'zero'
    else:
        lLogger.info("Bit0 of NVRAM 0x71 is '0', so we'll do not need to clear it.")
    
    #  Return boolean indicating whether we were successful or not
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,
                                               sScriptName, __version__)
    return (not bErrorsOccurred)
    

    
####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.info("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


