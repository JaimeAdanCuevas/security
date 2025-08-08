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
#| $Id: GrubForceSelectUntrustedItp.py 127 2015-02-02 23:34:01Z amr\egross $
#| $Date: 2015-02-02 15:34:01 -0800 (Mon, 02 Feb 2015) $
#| $Author: amr\egross $
#| $Revision: 127 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *   Make the "halt anyway" behavior a command line option rather than
#|       the default
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
import time         as _time
from optparse import OptionParser

# pythonsv imports
import common.toolbox    as _toolbox
import common.baseaccess as _baseaccess 
import itpii             as _itpii

## Global Variables/Constants
_itp                 = _itpii.baseaccess()
_log                 = _toolbox.getLogger()
_base                = _baseaccess.getglobalbase()

# Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 127 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
nTargetBitValueEnable   = 1
nTargetBitValueDisable  = 0

# val_tools DAL Utilities Import - gotta find it first!
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
import ValToolsDalUtilities as _ValToolsDalUtilities



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

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug   Option read as %s" % oCmdlineOptions.Debug   )
    _log.debug("Enable  Option read as %s" % oCmdlineOptions.Enable  )
    _log.debug("Disable Option read as %s" % oCmdlineOptions.Disable )

    #  Can't specify both Enable and Disable!
    if (oCmdlineOptions.Enable and oCmdlineOptions.Disable):
        _log.error("Both --enable and --disable options specified.  ")
        _log.error("   The doc cured my multiple personality order yesterday.")
        _log.error("   Sorry, but I can't both enable and disable that bit now.")
        _log.error("Exiting with non-zero status...")
        _sys.exit(1)

    #  If neither enable nor disable is specified, there's nothing to do!
    if (not oCmdlineOptions.Enable and not oCmdlineOptions.Disable):
        _log.error("Neither --enable nor --disable option specified.  ")
        _log.error("   I guess you didn't want me to do anything after all.")
        _log.error("Exiting with non-zero status...")
        _sys.exit(1)


    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Define exception class that indicates that some kind of failure happened 
#|  while trying to halt the system
#+----------------------------------------------------------------------------+
class eHaltException(Exception):
    pass


#+----------------------------------------------------------------------------+
#|  Halt the CPUs if they're not already halted
#|
#|  Since we don't know when this script will be run and it could be run
#|  during a reboot, we need to try a few times to ensure that we got
#|  the result we were looking for before proceeding
#|
#|  Inputs:     None
#|  Returns:    True:  if system was running (halt necessary)
#|              False: if system was already halted (no halt necessary)
#|
#|  Throws exception if something really bad happens
#|
#+----------------------------------------------------------------------------+
def haltIfNecessary():
    nNumCheckRetries = 60
    nNumHaltRetries  = 10

    #  First, check to see if the system is already halted
    while ((nNumCheckRetries >= 0) and (not  _base.isrunning())):
        _log.info("System detected in halted state. Waiting 10 sec to check again.")
        _log.info("    Will check %1d more times." % nNumCheckRetries)
        #  If it looks halted, wait 5sec and check again just to be sure.
        #  This helps account for running the script during a reboot, where
        #  isrunning() could return false if we just power-cycled the system
        #  This period appears to last somewhere between 5 and 30sec, so setting
        #  a timeout much larger than that
        nNumCheckRetries = nNumCheckRetries - 1
        if (nNumCheckRetries >= 0):
            _time.sleep(10)
            
    #  Check to see if the system is running or halted
    if (_base.isrunning()):
        #  The system is running and an itp.halt() is necessary
        _log.info("System detected in running state. Must be halted in order")
        _log.info("to access BIOS NVRAM.  Attemtping to halt CPUs... ")
    else:
        #  If we're still seeing the system halted, there's a good chance it's really halted
        _log.info("Successfully verified that system is already halted. No need to attempt itp.halt().")
        return(False)

    bHaltedSuccessfully = False

    #  Try to halt until we're successful or run out of retries
    while ((not bHaltedSuccessfully) and (nNumHaltRetries > 0)):
        nNumHaltRetries = nNumHaltRetries - 1
        if _ValToolsDalUtilities.tryHalt():
            _log.info("    System halted successfully.")
            bHaltedSuccessfully = True
        else:
            _log.error("    Failed to halt CPUs.  This is a critical step.")
            _log.error("    Will retry %2d more times..." % nNumHaltRetries)
            _time.sleep(1)

    #  If we exited the while loop and still haven't halted successfully,
    #  this is really bad.  Raise an Exception to let other code try to do
    #  something if possible.
    if not bHaltedSuccessfully:
        raise eHaltException('Failed to halt after 10 tries!')

    return(True)



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
    nNvramBitTargetValue    = -1
    bWasRunning             = False

    #  Startup tasks - get the logger configured
    _ValToolsDalUtilities.setupLogger(bDebug, sLogfileName)
    _ValToolsDalUtilities.printStartupBanner(nOutputWidth, 
                                             sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Determine if we're enabling or disabling ForceUntrusted mode
    #  and set variable storing the target bit value appropriately
    if (oCmdlineOptions.Enable):
        nNvramBitTargetValue = nTargetBitValueEnable
    elif (oCmdlineOptions.Disable):
        nNvramBitTargetValue = nTargetBitValueDisable
    else:
        _log.error("Neither --enable nor --disable option specified.  ")
        _log.error("   I guess you didn't want me to do anything after all.")
        return(0)

    #  Explain what we're doing and why
    _log.info("SIV uses bit0 of NVRAM offset 0x71 (BIOS Scratchpad) to indicate to") 
    _log.info("    GRUB whether to allow normal trusted boot (value=0) or to force") 
    _log.info("    a legacy (untrusted) boot (value=1).") 

    #  ITP version of this script must be executed while the CPUs are halted,
    #  because we'll be using thread0 to perform IO writes/reads
    try:
        bWasRunning = haltIfNecessary()
    except eHaltException as eException:
        _log.error("")
        _log.error("Some kind of really bad error happened while trying to halt the CPUs.")
        _log.error("    This is not something I can recover from.")
        _log.error("    Details of the error are:")
        _log.error("        * %s" % eException.args[0])
        _log.error("Since I couldn't halt the CPUs, I can't perform the actions for the rest of the script.")
        bErrorsOccurred = True

    #  If no errors encountered so far, continue with script execution
    if not bErrorsOccurred:
        #  If no errors have occurrred, then execute the main functionality 
        #  of the script.  
        #  
        #  The basic flow of the code below is:
        #  *   Write NVRAM offset (0x71) to index address (0x70)
        #  *   Read data address (0x71) to get current value of scratchpad register
        #  *   If data address has same value as target, we're done
        #  *   If data address has different value from target:
        #  *       Take current value and modify only the bit in question (bit0)
        #  *       Write new (byte) value to data address (0x71)
        #  *       Read and verify that new value was written
        #  *   Done
        #  
        #  This section has grown larger than originally
        #  planned, so ideally it should be broken up into separate functions
        #  TODO: break this section up in to functions for better readability
        #

        #  System call writing value 0x71 to CMOS register at offset 0x70
        _log.info("Setting NVRAM Index by writing value of 0x71 to IO address 0x70") 
        _log.info("    This prepares us to access NVRAM offset 0x71 via IO address 0x71") 
        #  Execute OS system command with try/except handling so we don't 
        #  just assume that the command completed successfully
        _log.info("    Command was: '%s'" % "_itp.threads[0].port(0x70,0x71)")
        try:
            _itp.threads[0].port(0x70,0x71)
        except Exception, ePort:
            _log.error("    ITP DAL command to write to IO address 0x70 failed.")
            _log.error("    This is a critical step, so I can't continue...")
            _log.error("    ITP Command Response: %s" % ePort)
            bErrorsOccurred = True
        else:
            _log.info("    ITP DAL command to write to IO address 0x70 completed succesfully.")

    #  If no errors encountered so far, continue with script execution
    #      Read data address (0x71) to get current value of scratchpad register
    if not bErrorsOccurred:
        #  Read the byte value from NVRAM by accessing IO address 0x71
        #  Note: this is extra confusing because we're using IO address 0x71
        #  to access NVRAM Index 0x71
        _log.info("Reading IO address 0x71 to get the NVRAM data...") 
        nNvramData = 0xFF
        #  Execute OS system command with try/except handling so we don't 
        #  just assume that the command completed successfully
        _log.info("    Command was: '%s'" % "_itp.threads[0].port(0x71)")
        try:
            nNvramData = _itp.threads[0].port(0x71)
        except Exception, ePort:
            _log.error("    ITP DAL command to read to IO address 0x71 failed.")
            _log.error("    This is a critical step, so I can't continue...")
            _log.error("    ITP Command Response: %s" % ePort)
            bErrorsOccurred = True
        else:
            _log.info("    Successfully read IO address 0x71 and got 0x%02x" % nNvramData)

    #  If no errors encountered so far, continue with script execution
    #      Check to see if data address has same value as target, take action if necessary
    if not bErrorsOccurred:
        nNewNvramByteValue = 0xFF
        #  Checking the last bit of value at offset 0x71 to determine if
        #  ForceUntrustedMode is currently set as desired
        if (nNvramData & (0x01) == nNvramBitTargetValue):
            #  If the current value matches the target value, we're done!
            _log.info("NVRAM offset 0x71 is 0x%01x, and bit0 matches the target" % nNvramData)
            _log.info("    value of 0x%01x.  No action necessary." % nNvramBitTargetValue)
        else:
            #  If the current value doesn't match the target value,
            #  we have work to do...
            _log.info("NVRAM offset 0x71 is 0x%01x, and bit0 does not match the target" % nNvramData)
            _log.info("    target value of 0x%01x.  Writing target value to NVRAM." % nNvramBitTargetValue)
            
            #  Use a bitmask and bitwise logical operator to change
            #  only the bit we're intereseted in, since IO writes
            #  modify an entire byte (8bits)
            if (nNvramBitTargetValue == 1):
                nNewNvramByteValue= (nNvramData | 0x01)
            else:
                nNewNvramByteValue= (nNvramData & 0xFE)
    
            _log.info("Value(dword) to be written to NVRAM: 0x%02x" % nNewNvramByteValue)
        
            #  Writing the new value (with last bit changed) to address 0x71
            _log.info("    Command was: '%s'" % "_itp.threads[0].port(0x71, nNewNvramByteValue)")
            try:
                _itp.threads[0].port(0x71, nNewNvramByteValue)
            except Exception, ePort:
                bErrorsOccurred = True
                _log.error("    ITP DAL command to write to IO address 0x71 failed.")
                _log.error("    ITP Command Response: %s" % ePort)
            else:
                _log.info("    ITP DAL command to write to IO address 0x71 completed succesfully.")
    
            #  Read the value from NVRAM to ensure it actually got written
            _log.info("Reading IO address 0x71 to verify the NVRAM data...") 
            nNvramData = 0xFF
            _log.info("    Command was: '%s'" % "_itp.threads[0].port(0x71)")
            try:
                nNvramData = _itp.threads[0].port(0x71)
            except Exception, ePort:
                bErrorsOccurred = True
                _log.error("    ITP DAL command to read to IO address 0x71 failed.")
                _log.error("    This is a critical step, so I can't continue...")
                _log.error("    ITP Command Response: %s" % ePort)
            else:
                _log.info("    Successfully read IO address 0x71 and got 0x%02x" % nNvramData)

            #  Checking the last bit of value at offset 0x71 to determine if
            #  ForceUntrustedMode is now set as desired
            if (nNvramData == nNewNvramByteValue):
                _log.info("NVRAM data now verified as 0x%02x, which is what we expected."
                          % nNewNvramByteValue)
            else:
                _log.error("NVRAM data NOT verified.  ")
                _log.error("   Read:     0x%02x" % nNvramData)
                _log.error("   Expected: 0x%02x" % nNewNvramByteValue)
                bErrorsOccurred = True

    #  If the system was running (not halted) when we started the script,
    #  we need to return it to that state.
    if bWasRunning:
        _log.info("System started out in running state. Returning to running state at conclusion of script...")
        if _ValToolsDalUtilities.tryGo():
            _log.info("System exited Probe Mode (via itp.go()) successfully.  Continuing...")
        else:
            _log.error("Failed to exit Probe Mode for all CPUs.  Check you system for errors.")
            bErrorsOccurred = True
    
    #  Return boolean indicating whether we were successful or not
    _ValToolsDalUtilities.printFinishingBanner(bErrorsOccurred, nOutputWidth,
                                               sScriptName, __version__)
    return (not bErrorsOccurred)
    

####################################################################################

if __name__ == '__main__':
    if main():
        _log.result("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        _log.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


