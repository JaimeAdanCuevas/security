#!/usr/bin/env python
#+----------------------------------------------------------------------------+
#| INTEL CONFIDENTIAL
#| Copyright 2015 Intel Corporation All Rights Reserved.
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
#| $Id: ResetSystemLinux.py 147 2015-03-11 05:01:28Z amr\egross $
#| $Date: 2015-03-10 22:01:28 -0700 (Tue, 10 Mar 2015) $
#| $Author: amr\egross $
#| $Revision: 147 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  Change language to refer to OS restart and OS shutdown for graceful
#|      entries
#+----------------------------------------------------------------------------+

"""
    Script to give user the ability to reset the system in a variety of ways
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
import time         as _time
from optparse import OptionParser

## Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + ""  #  <--- make sure this is the correct relative path!
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
#|  Section for SIV-specific constants and technical definitions
#+----------------------------------------------------------------------------+

# From Patsburg PCH C-Spec 14.1.5 (Reset Control Regiseter definition)
nResetControlOffset = 0xCF9
dOffsetRstctlBits   = dict(
                            FULL_RST   = 0x3,
                            RST_CPU    = 0x2,
                            SYS_RST    = 0x1,
                      )

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

    parser.add_option("--surprise", action="store_true", dest="Surprise", 
                      default=False,
                      help="Indicates script should cause the reset without the OS's \
                            knowledge/preparation.  For example an S5 reset could be\
                            done by the Linux 'shutdown -P' command, but a surprise S5\
                            could be done by a write to 0xCF9.")

    parser.add_option("--type", action="store", dest="Type", 
                      type="choice", default="Undefined", 
                      choices=["G2", "CPU", "CPU-PCI", "OS-Restart", "Undefined"],
                      help="Indicates what type of reset the script should attempt\
                            OS-Restart: Restart the system via the OS-specific\
                                        restart command, such as 'shutdown -r'\
                            CPU:        Reset only the CPU via the INIT# signal\
                            CPU-PCI:    CPU reset and do a PCI reset\
                            G2:         (a.k.a. S5) Shut down the system with loss\
                                        of all power but Standby; could be done by\
                                        a write to 0xCF9.")

    parser.add_option("--notify_automation", action="store_true", dest="NotifyAutomation", 
                      default=False,
                      help="Indicates script should stop the HostExec service prior to \
                            resetting the system.  In the automation context, this is\
                            necessary to ensure that the automation server knows this\
                            reset is intentional and not an error condition.")

    parser.add_option("--fake_reset", action="store_true", dest="FakeReset", 
                      default=False,
                      help="Indicates script should not acutally reset the system\
                            This is used during script debug so that the script can\
                            be run multiple times without waiting for the system\
                            to actually reset.")

    parser.add_option("--delay", action="store", dest="ResetDelay", type=int,
                      default=0,
                      help="Indicates an optional delay (in seconds) to introduce\
                            before resetting the system.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug            Option read as %s"  % oCmdlineOptions.Debug           )
    lLogger.debug("Surprise         Option read as %s" % oCmdlineOptions.Surprise         )
    lLogger.debug("Type             Option read as %s" % oCmdlineOptions.Type             )
    lLogger.debug("NotifyAutomation Option read as %s" % oCmdlineOptions.NotifyAutomation )
    lLogger.debug("FakeReset        Option read as %s" % oCmdlineOptions.FakeReset        )
    lLogger.debug("ResetDelay       Option read as %s" % oCmdlineOptions.ResetDelay       )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Check Command Line Options for errors
#|
#|  Look for invalid combinations of options
#|
#|  Inputs:     Command Line Options Object from OptionParser
#|  Returns:    1 on success; 0 otherwise
#|
#+----------------------------------------------------------------------------+
def checkCommandLineOptions(oCmdlineOptions):
    bSurprise   = oCmdlineOptions.Surprise
    sType       = oCmdlineOptions.Type
    if (sType == "Undefined"):
        lLogger.error("Reset Type not specified!  I don't know what to do.")
        return 0
    return 1


#+----------------------------------------------------------------------------+
#|  Wait for the specified amount of time
#|
#|  Inputs:     integer number of seconds to wait
#|  Returns:    1 on success; 0 otherwise
#|
#+----------------------------------------------------------------------------+
def waitForDelay(nDelay):
    lLogger.info("Delay of %4d seconds requested.  Waiting..." % nDelay)
    _time.sleep(nDelay)
    lLogger.info("    Done with delay... proceeding with script.")
    return 1


#+----------------------------------------------------------------------------+
#|  Assembles the appropriate value to write to the Reset Control register
#|  that will initiate the desired type of reset.  Then write that value
#|  to the register to initiate the reset.
#|
#|  Inputs:     
#|              Type of Reset to perform
#|              Boolean indicating whether it's a surprise or graceful reset
#|              Boolean indicating whether to actually reset the system or
#|                  just print the command we'd normally execute
#|
#|  Returns:    1 on success; 0 otherwise
#|
#+----------------------------------------------------------------------------+
def writeResetRegister(sType, bSurprise, bFakeReset):

    # Dictionary stores the bit positions of the bits of interest,
    # so to assemble a value to write to the register, we have to 
    # left-shift a '1' to the appropriate position
    nResetCpuOnly    = (1 << dOffsetRstctlBits["RST_CPU"])
    nSystemResetOnly = (1 << dOffsetRstctlBits["SYS_RST"])
    nFullResetOnly   = (1 << dOffsetRstctlBits["FULL_RST"])
    
    # /usr/local/uvat/bin/ReBootSUTA CPU Reset involves setting only the CPU Reset bit
    nCpuResetRegVal     = nResetCpuOnly

    # A CPU/PCI Reset involves setting the CPU Reset bit AND the System Reset bit
    nCpuPciResetRegVal  = nResetCpuOnly | nSystemResetOnly

    # A G2 Reset involves setting the CPU, System, and Full Reset bits
    nG2ResetRegVal    = nResetCpuOnly | nSystemResetOnly | nFullResetOnly

    # ACPI G2/S5 Reset
    if   (sType == "G2"):
        # Surprise version
        if (bSurprise):
            lLogger.info("Surprise G2(S5) Reset requested.  Executing...")
            sCommand = "outb 0x%x 0x%x" % (nResetControlOffset, nG2ResetRegVal)
            lLogger.debug("Command was: %s" % sCommand)
            sDescription = "reset system via IO write to 0xCF9 with value 0xE"
            bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=bFakeReset)
            if not bSuccess:
                return 0
        # Graceful (OS assisted) version
        else:
            # Execute: shutdown -P now
            lLogger.info("Graceful G2(S5) Reset requested.  Executing...")
            sCommand = "shutdown -P now"
            lLogger.debug("Command was: %s" % sCommand)
            sDescription = "shut down the system via the '%s' command" % (sCommand)
            bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=bFakeReset)
            if not bSuccess:
                return 0
    # CPU-only Reset
    elif (sType == "CPU"):
        # Surprise version
        if (bSurprise):
            lLogger.info("Surprise CPU Reset requested.  Executing...")
            sCommand = "outb 0x%x 0x%x" % (nResetControlOffset, nCpuResetRegVal)
            lLogger.debug("Command was: %s" % sCommand)
            sDescription = "reset CPU only via IO write to 0xCF9 with value 0x4"
            bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=bFakeReset)
            if not bSuccess:
                return 0
        # Graceful (OS assisted) version
        else:
            lLogger.error("I don't know how to do a graceful CPU Reset; only surprise.  Sorry.")
            return 0
    # CPU and PCI Reset
    elif (sType == "CPU-PCI"):
        # Surprise version
        if (bSurprise):
            # Execute: CF9=0x6
            lLogger.info("Surprise CPU/PCI Reset requested.  Executing...")
            sCommand = "outb 0x%x 0x%x" % (nResetControlOffset, nCpuPciResetRegVal)
            lLogger.debug("Command was: %s" % sCommand)
            sDescription = "reset CPU and PCI/e via IO write to 0xCF9 with value 0x6"
            bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=bFakeReset)
            if not bSuccess:
                return 0
        # Graceful (OS assisted) version
        else:
            lLogger.error("I don't know how to do a graceful CPU/PCI Reset; only surprise.  Sorry.")
            return 0
    # OS Restart
    elif (sType == "OS-Restart"):
        # Surprise version
        if (bSurprise):
            lLogger.error("'OS-Restart' does not have a 'surprise' variant because this action")
            lLogger.error("    implicitly requires the OS's knowledge/interaction.  Sorry.")
            return 0
        # Graceful (OS assisted) version
        else:
            # Execute: shutdown -r now
            lLogger.info("OS Restart requested.  Executing...")
            sCommand = "shutdown -r now"
            lLogger.debug("Command was: %s" % sCommand)
            sDescription = "restart the system via the '%s' command" % (sCommand)
            bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=bFakeReset)
            if not bSuccess:
                return 0

    # Unknown Reset request (error)
    else:
        lLogger.error("Unknown reset type specified.  This shouldn't happen.")
        return 0

    return 1

#+----------------------------------------------------------------------------+
#|  Assembles the appropriate value to write to the Reset Control register
#|  that will initiate the desired type of reset.  Then write that value
#|  to the register to initiate the reset.
#|
#|  Inputs:     
#|              Type of Reset to perform
#|              Boolean indicating whether it's a surprise or graceful reset
#|
#|  Returns:    1 on success; 0 otherwise
#|
#+----------------------------------------------------------------------------+
def notifyAutomation():

    lLogger.info("NotifyAutomation requested.  Stopping HostExec gracefully...")

    # Sleep for 5 sec in case this was run via automation's BackgroundCmd
    # function; this gives the command time to give a return value to 
    # the automation server so it doesn't freak out
    _time.sleep(5)

    # Gracefully stop the HostExec service to let automation know the
    # upcoming restart is expected
    sCommand = "service HostExec stop"
    lLogger.debug("Command was: %s" % sCommand)
    sDescription = "gracefully shut down the automation HostExec service."
    bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                bCriticalStep=True, bVerbose=True)
    # Sleep for 5 sec to allow HostExec to actually shut down before proceeding
    _time.sleep(5)

    return bSuccess

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
    bErrorsOccurred = not checkCommandLineOptions(oCmdlineOptions)

    #  If user requested a delay before reset, do that
    if (oCmdlineOptions.ResetDelay > 0):
        bErrorsOccurred = not waitForDelay(oCmdlineOptions.ResetDelay)

    #  If we need to interact with the automation server, do so
    if (oCmdlineOptions.NotifyAutomation):
        bErrorsOccurred = not notifyAutomation()

    #  Perform reset as requested by user
    if (not bErrorsOccurred):
        bErrorsOccurred = (not writeResetRegister(oCmdlineOptions.Type,
                                                  oCmdlineOptions.Surprise,
                                                  oCmdlineOptions.FakeReset))

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


