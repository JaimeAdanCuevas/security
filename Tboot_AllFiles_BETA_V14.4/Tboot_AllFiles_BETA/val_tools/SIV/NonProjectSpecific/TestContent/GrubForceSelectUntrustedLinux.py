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
#| $Id: GrubForceSelectUntrustedLinux.py 137 2015-02-03 01:11:18Z amr\egross $
#| $Date: 2015-02-02 17:11:18 -0800 (Mon, 02 Feb 2015) $
#| $Author: amr\egross $
#| $Revision: 137 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    This script sets or clears a BIOS scratchpad register that causes SIV's
    custom Grub code to force the system to boot in legacy (untrusted) mode.

    This script comes in two flavors:  
        *   Linux OS-based script
        *   PythonSV/DAL-based script

    The reason for the two versions is that the OS-based version is only 
    usable when the system is booting properly to the OS.  To recover a system
    that is not booting to the OS, one should use the PythonSV/DAL version.

    The primary use of this script is to allow unattended recovery of a system
    that is stuck in an SINIT loop due to some failure in the trusted boot
    sequence.  Normally, the SINIT ACM will detect an anomoly and reset the
    system prior to the OS booting; this results in an endless reboot cycle.
    Since the OS never boots, an SUT-based command to recover the system won't
    work.  Thus, the ITP version of this script will set a BIOS scratchpad
    register that will cause Grub to select an untrusted boot on the next boot
    so that the system can be recovered.

    Note that the system will continue to be forced to boot in an untrusted
    mode until this BIOS scratchpad register is cleared, so don't forget
    to clear it after recovering the system.
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
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 137 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
nTargetBitValueEnable   = 1
nTargetBitValueDisable  = 0

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "../../../../Generic/NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
if (bDebug): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDebug):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

#  Since we may want to import functionality from this script into another script,
#  only create the Logger instance if this is executing as a script and not being
#  imported as a module
if __name__ == '__main__':
    lLogger = _ValToolsUtilities.setupLogger(bDebug, sLogfileName)

#+----------------------------------------------------------------------------+
#|  Handle Command Line Options
#|
#|  This functon defines all supported command line options and invokes the
#|  methods used to extract those options from the user-supplied command line
#|
#|  Inputs:     None
#|  Returns:    Command Line Options Object from OptionParser
#|
#+----------------------------------------------------------------------------+
def parseCommandLine():

    #  Create a parser object and add options to it
    parser = OptionParser()
    parser.add_option("--debug", action="store_true",
                      dest="Debug", default=False,
                      help="Turn on DEBUG functionality of script.")

    parser.add_option("--enable", action="store_true", dest="Enable", 
                      default=False,
                      help="Sets BIOS scratchpad bit that causes Grub to select untrusted(legacy) boot mode")

    parser.add_option("--disable", action="store_true", dest="Disable", 
                      default=False,
                      help="Clears BIOS scratchpad bit that causes Grub to select untrusted(legacy) boot mode")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Enable  Option read as %s" % oCmdlineOptions.Enable    )
    lLogger.debug("Disable Option read as %s" % oCmdlineOptions.Disable   )
    lLogger.debug("Debug   Option read as %s" % oCmdlineOptions.Debug     )

    #  Can't specify both Enable and Disable!
    if (oCmdlineOptions.Enable and oCmdlineOptions.Disable):
        lLogger.error("Both --enable and --disable options specified.  ")
        lLogger.error("   The doc cured my multiple personality order yesterday.")
        lLogger.error("   Sorry, but I can't both enable and disable that bit now.")
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)

    #  If neither enable nor disable is specified, there's nothing to do!
    if (not oCmdlineOptions.Enable and not oCmdlineOptions.Disable):
        lLogger.error("Neither --enable nor --disable option specified.  ")
        lLogger.error("   I guess you didn't want me to do anything after all.")
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug  Option read as %s"  % oCmdlineOptions.Debug        )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Determines the target NVRAM bit value by examining command line options
#|
#|
#|  Inputs:     
#|              Boolean indicating whether we're enabling the bit
#|              Boolean indicating whether we're disabling the bit
#|
#|  Returns:    Bit value on success; -1 on error
#|
#+----------------------------------------------------------------------------+
def getTargetNvramValue(bEnable, bDisable):
    nNvramBitTargetValue    = -1

    if (bEnable):
        nNvramBitTargetValue = nTargetBitValueEnable
    elif (bDisable):
        nNvramBitTargetValue = nTargetBitValueDisable
    else:
        lLogger.error("Neither --enable nor --disable option specified.  ")
        lLogger.error("   I guess you didn't want me to do anything after all.")

    return(nNvramBitTargetValue)



#+----------------------------------------------------------------------------+
#|  Writes a byte value to the NVRAM offset specified
#|
#|
#|  Inputs:     
#|              Logger object
#|              NVRAM offset to access
#|              Value to write to NVRAM offset
#|              Description of what we're writing
#|              Boolean indicating whether we're in debug mode or not
#|
#|  Returns:    True on success; False otherwise
#|
#+----------------------------------------------------------------------------+
def writeNvramValue(lLogger, nOffset, nValue, sDescription, bDebug):

    #  Run actual command to write the value
    sCommand        = "outb 0x%x 0x%x" % (nOffset, nValue)
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    lLogger.info("    Successfully wrote IO address 0x%02x with data 0x%02x" % (nOffset, nValue))

    return bSuccess


#+----------------------------------------------------------------------------+
#|  Writes a byte value to the NVRAM offset specified
#|
#|
#|  Inputs:     
#|              Logger object
#|              NVRAM offset to access
#|              Description of what we're reading
#|              Boolean indicating whether we're in debug mode or not
#|
#|  Returns:    Bit value on success; -1 on error
#|
#+----------------------------------------------------------------------------+
def readNvramValue(lLogger, nOffset, sDescription, bDebug):
    sNvramData = None

    #  Run actual command to read the value
    sCommand = "inb 0x%x" % (nOffset)
    try:
        sNvramData = _ValToolsUtilities.returnOsCommand( lLogger, sCommand, sDescription, 
                                                         bVerbose=True, bDoNotRun=bDebug)
    #  Output error message and reraise exception
    except Exception, eIoRead:
        lLogger.error("    OS command to %s failed" % sDescription)
        lLogger.error("    This is a critical step, so I can't continue...")
        lLogger.error("    Error output was: %s", eIoRead)
        raise eIoRead

    #  Process output if no exceptions
    nNvramData = int(sNvramData)
    lLogger.info("    Successfully read IO address 0x%02x and got 0x%02x" % (nOffset, nNvramData))

    return nNvramData

#+----------------------------------------------------------------------------+
#|  Indicates whether the current value and the target value match, after
#|  applying a bitmask to the current value
#|
#|  Inputs:     
#|              Logger object
#|              Current value read from NVRAM
#|              Target value we want to be in NVRAM
#|              Bitmask to apply to the current value
#|
#|  Returns:    True if values are different; False otherwise
#|
#+----------------------------------------------------------------------------+
def needToChangeNvram(lLogger, nCurrentValue, nTargetValue, nBitMask):
    bNewValueIsDifferent    =   True

    #  Apply the bitmask to the current value and compare
    if (nCurrentValue & (nBitMask) == nTargetValue):
        #  If the current value matches the target value, we're done!
        lLogger.info("NVRAM offset 0x71 is 0x%01x, and bit0 matches the target" % nCurrentValue)
        lLogger.info("    value of 0x%01x.  No action necessary." % nTargetValue)
        bNewValueIsDifferent = False
    else:
        #  If the current value doesn't match the target value,
        #  we have work to do...
        lLogger.info("NVRAM offset 0x71 is 0x%01x, and bit0 does not match the target" % nCurrentValue)
        lLogger.info("    target value of 0x%01x.  Writing target value to NVRAM." % nTargetValue)
        bNewValueIsDifferent = True

    return bNewValueIsDifferent


#+----------------------------------------------------------------------------+
#|  Calculates new value to write to NVRAM based on target bit value and 
#|  current NVRAM value.  This function assumes the bit of interest is bit0
#|  and we're dealing with byte values
#|
#|  Inputs:     
#|              Logger object
#|              Current value read from NVRAM
#|              Target value we want to be in NVRAM
#|              Bitmask to apply to the current value
#|
#|  Returns:    True if values are different; False otherwise
#|
#+----------------------------------------------------------------------------+
def getNewNvramTargetValue(lLogger, nNvramBitTargetValue, nOldNvramData):
    nNewNvramTargetValue = None

    #  Use a bitmask and bitwise logical operator to change
    #  only the bit we're intereseted in, since IO writes
    #  modify an entire byte (8bits)
    if (nNvramBitTargetValue == 1):
        nNewNvramTargetValue= (nOldNvramData | 0x01)
    elif (nNvramBitTargetValue == 0):
        nNewNvramTargetValue= (nOldNvramData & 0xFE)
    else:
        lLogger.error("Something other than 0 or 1 specified for Target Bit Value(=%d)" % nNvramBitTargetValue)
    
    lLogger.info("Value(dword) to be written to NVRAM: 0x%02x" % nNewNvramTargetValue)
        
    return nNewNvramTargetValue


#+----------------------------------------------------------------------------+
#|  Determines target bit value from function arguments; reads NVRAM to
#|  determine current value; if current value does not match target value,
#|  writes new value to NVRAM; verifies write was successful
#|
#|  Inputs:     
#|              Logger object
#|              Boolean indicating whether we're enabling the bit
#|              Boolean indicating whether we're disabling the bit
#|
#|  Returns:    True if successful; False otherwise
#|
#+----------------------------------------------------------------------------+
def writeNvramIfNecessary(lLogger, bEnable, bDisable):
    bErrorsOccurred     = False # used to short-circuit certain steps if errors found
    nOldNvramData       = 0xFF

    #  Determine if we're enabling or disabling ForceUntrusted mode
    #  and set variable storing the target bit value appropriately
    nNvramBitTargetValue = getTargetNvramValue(bEnable, bDisable)
    if (nNvramBitTargetValue == -1):
        lLogger.error("I can't determine a valid target NVRAM bit value.  I can't continue.")
        return 0


    #  Explain what we're doing and why
    lLogger.info("SIV uses bit0 of NVRAM offset 0x71 (BIOS Scratchpad) to indicate to") 
    lLogger.info("    GRUB whether to allow normal trusted boot (value=0) or to force") 
    lLogger.info("    a legacy (untrusted) boot (value=1).") 

    #  The basic flow of the code below is:
    #  *   Write NVRAM offset (0x71) to index address (0x70)
    #  *   Read data address (0x71) to get current value of scratchpad register
    #  *   If data address has same value as target, we're done
    #  *   If data address has different value from target:
    #  *       Take current value and modify only the bit in question (bit0)
    #  *       Write new (byte) value to data address (0x71)
    #  *       Read and verify that new value was written
    #  *   Done

    #  System call writing value 0x71 to CMOS register at offset 0x70
    sDescription = "set NVRAM Index by writing value of 0x71 to IO address 0x70" 
    bErrorsOccurred = not writeNvramValue(lLogger, 0x70, 0x71, sDescription, bDebug)

    #  If the previous command failed, we're don't bother with the rest
    if bErrorsOccurred:
        lLogger.error("    OS command to %s failed" % sDescription)
        lLogger.error("    This is a critical step, so I can't continue...")
    #  If no errors encountered so far, continue with script execution
    ######################################
    else:
        #  Read data address (0x71) to get current value of scratchpad register
        #  Do this by reading the byte value from NVRAM by accessing IO
        #  address 0x71
        #  
        #  Note: this is extra confusing because we're using IO address 0x71
        #  to access NVRAM Index 0x71
        sDescription = "read NVRAM data by reading IO address 0x71" 
        try:
            nOldNvramData = readNvramValue(lLogger, 0x71, sDescription, bDebug)
        except Exception, eIoRead:
            if bDebug:
                lLogger.info("    Running in debug mode, so ignoring previous command failure.")
                nOldNvramdata = 0x0
            else:
                lLogger.info("    Previous command failed, so I'm done.")
                lLogger.info("    Error message was %s" % eIoRead)
                bErrorsOccurred = True

    ######################################
    #  If no errors encountered so far, continue with script execution
    #  Check to see if data address has same value as target, take action if necessary
    if not bErrorsOccurred:
        #  Check to see if the current value already matches the target
        #  We only care about the last bit, so the bitmask is 0x01
        if (needToChangeNvram(lLogger, nOldNvramData, nNvramBitTargetValue, 0x01)):
            #  Determine the byte value to write to NVRAM, given that we
            #  can't just write a single bit at a time
            nNewNvramTargetValue = getNewNvramTargetValue(lLogger, nNvramBitTargetValue, nOldNvramData)

            #  Write the new value to NVRAM
            sDescription = "write new value of 0x%02x to IO address 0x71" % nNewNvramTargetValue  
            bErrorsOccurred = not writeNvramValue(lLogger, 0x71, nNewNvramTargetValue, sDescription, bDebug)

            #  Read the value from NVRAM to ensure it actually got written
            nNewNvramData = 0xFF
            sDescription = "read IO address 0x71 to verify new NVRAM data" 
            try:
                nNewNvramData = readNvramValue(lLogger, 0x71, sDescription, bDebug)
            except:
                if bDebug:
                    nNewNvramData = 0xFE
                else:
                    bErrorsOccurred = True

            #  Checking the last bit of value at offset 0x71 to determine if
            #  ForceUntrustedMode is now set as desired
            if (nNewNvramData == nNewNvramTargetValue):
                lLogger.info("NVRAM data now verified as 0x%02x, which is what we expected."
                             % nNewNvramTargetValue)
            else:
                lLogger.error("NVRAM data NOT verified.  ")
                lLogger.error("   Read:     0x%02x" % nNewNvramData)
                lLogger.error("   Expected: 0x%02x" % nNewNvramTargetValue)
                bErrorsOccurred = True

    return not bErrorsOccurred


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
    bErrorsOccurred = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    bErrorsOccurred = not writeNvramIfNecessary(lLogger, oCmdlineOptions.Enable, oCmdlineOptions.Disable)
    
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
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


