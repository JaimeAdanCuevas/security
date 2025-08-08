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
#| $Id: ModifyIptDalBreaks.py 206 2015-11-25 19:09:04Z egross $
#| $Date: 2015-11-25 11:09:04 -0800 (Wed, 25 Nov 2015) $
#| $Author: egross $
#| $Revision: 206 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    This script enables/disables various ITP control variable breaks.  It also
    does an itp.halt() and an itp.go() to actually modify those breaks if
    necessary.
"""
# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
from optparse import OptionParser

# pythonsv imports
import common.toolbox as _toolbox
import itpii
import common.baseaccess as _baseaccess
import ValToolsDalUtilities as ValToolsDalUtilities

# Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 206 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
base                    = _baseaccess.getglobalbase()
base_itpii              = itpii.baseaccess()

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../Utilities"  #  <--- make sure this is the correct relative path!
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

    parser.add_option("--shutdownbreak", action="store", dest="ShutdownBreak", 
                      type="choice", choices=["Unchanged", "False", "True"], default="Unchanged",
                      help="Set value of itp.cv.shutdownbreak in the ITP DAL")

    parser.add_option("--resetbreak", action="store", dest="ResetBreak", 
                      type="choice", choices=["Unchanged", "0", "1"], default="Unchanged",
                      help="Set value of itp.cv.resetbreak in the ITP DAL")

    parser.add_option("--machinecheckbreak", action="store", dest="MachineCheckBreak", 
                      type="choice", choices=["Unchanged", "False", "True"], default="Unchanged",
                      help="Set value of itp.cv.machinecheckbreak in the ITP DAL")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug             Option read as %s" % oCmdlineOptions.Debug            )
    _log.debug("ShutdownBreak     Option read as %s" % oCmdlineOptions.ShutdownBreak    )
    _log.debug("ResetBreak        Option read as %s" % oCmdlineOptions.ResetBreak       )
    _log.debug("MachineCheckBreak Option read as %s" % oCmdlineOptions.MachineCheckBreak)

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Function To Print Generic Finishing Banner
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def evaluateCurrentBreakStatus(sCmdlineOptionBreak, sDalBreakStatus):
    bModifyingBreak      = False # to indicate whether we need to change DAL control variable

    #  Figure out if we need to change the ITP DAL Break
    if (sCmdlineOptionBreak == "Unchanged"):
        _log.debug("DEBUG: Not modifying itp.cv.******break because command line options is set to 'Unchanged'")
        bModifyingBreak =  False
    else:
        _log.debug("DEBUG: itp.cv.******break     is currently set to: '%s'" % sDalBreakStatus)
        # Note: we need to format the output of the base_itp call as a string
        #       or the following comparison won't work
        bModifyingBreak = not (sDalBreakStatus == sCmdlineOptionBreak)

        # Output to help with debug of values received from ITP DAL
        if (sDalBreakStatus     == sCmdlineOptionBreak):
            _log.debug("DEBUG: Command line request and current ITP DAL status are     the same!")
            _log.debug("DEBUG:     ITP:'%s' vs. ScriptCmdline:'%s'" % (sDalBreakStatus, sCmdlineOptionBreak))
        else:
            _log.debug("DEBUG: Command line request and current ITP DAL status are not the same!")
            _log.debug("DEBUG:     ITP:'%s' vs. ScriptCmdline:'%s'" % (sDalBreakStatus, sCmdlineOptionBreak))

    return bModifyingBreak


#+----------------------------------------------------------------------------+
#|  Indicate whether we need to modify any breaks or not
#|
#|  Inputs:     
#|              base_itpii:             used to query ITP DAL break status
#|              oCmdlineOptions:        object containing script command
#|                                      line options
#|              bModifyingShutdown:     bool indicating whether we need to
#|                                      modify this ITP DAL break
#|              bModifyingReset:        bool indicating whether we need to
#|                                      modify this ITP DAL break
#|              bModifyingMachineCheck: bool indicating whether we need to
#|                                      modify this ITP DAL break
#|              nEnabledThread:         index of enabled thread in the 
#|                                      itp.threads data structure
#|  
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
#  Indicate whether we need to modify anything or not
def logIntendedModifications(base_itpii, oCmdlineOptions, bModifyingShutdown, bModifyingReset, bModifyingMachineCheck, nEnabledThread):

    if (bModifyingShutdown):
        _log.info("    Attempting to modify itp.cv.shutdownbreak to %s" % oCmdlineOptions.ShutdownBreak)
    else:
        _log.info("NOT Attempting to modify itp.cv.shutdownbreak, because its current value is %s" % base_itpii.threads[nEnabledThread].cv.shutdownbreak)

    if (bModifyingReset):
        _log.info("    Attempting to modify itp.cv.resetbreak to %s" %  oCmdlineOptions.ResetBreak)
    else:
        _log.info("NOT Attempting to modify itp.cv.resetbreak, because its current value is %s" % base_itpii.threads[nEnabledThread].cv.resetbreak)

    if (bModifyingMachineCheck):
        _log.info("    Attempting to modify itp.cv.machinecheckbreak to %s" % oCmdlineOptions.MachineCheckBreak)
    else:
        _log.info("NOT Attempting to modify itp.cv.machinecheckbreak, because its current value is %s" % base_itpii.threads[nEnabledThread].cv.machinecheckbreak)

    return True

#+----------------------------------------------------------------------------+
#|  Modifies ITP DAL break settings as indicated by the input booleans
#|  Contains code to trap execeptions and report them to the user
#|  Attempts all modifications, even if a previous one failed
#|
#|  Inputs:     
#|              base_itpii:             used to query ITP DAL break status
#|              oCmdlineOptions:        object containing script command
#|                                      line options
#|              bModifyingShutdown:     bool indicating whether we need to
#|                                      modify this ITP DAL break
#|              bModifyingReset:        bool indicating whether we need to
#|                                      modify this ITP DAL break
#|              bModifyingMachineCheck: bool indicating whether we need to
#|                                      modify this ITP DAL break
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def ModifyBreaks(base_itpii, oCmdlineOptions, bModifyingShutdown, bModifyingReset, bModifyingMachineCheck):
    bErrorsOccurred = False 

    if (bModifyingShutdown):
        _log.info("Attempting to set itp.cv.shutdownbreak to %s" % oCmdlineOptions.ShutdownBreak)
        try:
            base_itpii.cv.shutdownbreak     = oCmdlineOptions.ShutdownBreak
        except Exception, eShutdown:
            _log.error("\n\001ired\001ERROR: Failed to modify shutdownbreak")
            _log.error("       ITP error: %s" %eShutdown)
        else:
            _log.error("\001igreen\001SUCCESS: set shutdownbreak to %s\n" % oCmdlineOptions.ShutdownBreak)

    if (bModifyingReset):
        _log.info("Attempting to set itp.cv.resetbreak to %s" %  oCmdlineOptions.ResetBreak)
        try:
            base_itpii.cv.resetbreak        = oCmdlineOptions.ResetBreak
        except Exception, eReset:
            _log.error("\n\001ired\001ERROR: Failed to modify resetbreak")
            _log.error("       ITP error: %s" %eReset)
        else:
            _log.error("\001igreen\001SUCCESS: set resetbreak to %s\n" % oCmdlineOptions.ResetBreak)

    if (bModifyingMachineCheck):
        _log.info("Attempting to set itp.cv.machinecheckbreak to %s" % oCmdlineOptions.MachineCheckBreak)
        try:
            base_itpii.cv.machinecheckbreak = oCmdlineOptions.MachineCheckBreak
        except Exception, eMachineCheck:
            _log.error("\n\001ired\001ERROR: Failed to modify machinecheckbreak")
            _log.error("       ITP error: %s" %eMachineCheck)
        else:
            _log.error("\001igreen\001SUCCESS: set machinecheckbreak to %s\n" % oCmdlineOptions.MachineCheckBreak)

    return (not bErrorsOccurred)


#+----------------------------------------------------------------------------+
#|  Looks through the available threads in the system and finds the first one
#|  that's enabled.  Returns invalid number (-1) if no enabled threads found
#|
#|  Inputs:     
#|              base_itpii:             used to query ITP DAL break status
#|
#|  Returns:    index in ITP threads[] array for the first enabled thread;
#|              or -1 if no threads found.
#|
#+----------------------------------------------------------------------------+
def FindEnabledThread(base_itpii):
    nFirstEnabledThread = -1

    _log.info("Looking at threads to see if we can find one that's enabled...")
    #  Loop through all the threads available in the ITP DAL data structure
    for nThread in range (len(base_itpii.threads)) :
        #  If we find one that's both valid and enabled, that's what we're
        #  looking for!
        if ( base_itpii.threads[nThread].isvalid and base_itpii.threads[nThread].isenabled ):
            _log.info("    examined thread %d ... and it was enabled! " % nThread)
            nFirstEnabledThread = nThread
            break
        #  If not, then inform user in debug mode and move to next thread
        else:
            _log.debug("    examined thread %d... and it was disabled.  Checking next thread." % nThread)
    return (nFirstEnabledThread)


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
    bModifyingShutdown      = False # to indicate whether we need to change DAL control variable
    bModifyingReset         = False # to indicate whether we need to change DAL control variable
    bModifyingMachineCheck  = False # to indicate whether we need to change DAL control variable
    bProbeModeNeeded        = False # indicates whether we need a halt/go sequence


    #  Startup tasks - get the logger configured
    _ValToolsDalUtilities.setupLogger(bDebug, sLogfileName)
    _ValToolsDalUtilities.printStartupBanner(nOutputWidth, 
                                             sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Warn user if there's nothing to do
    if (oCmdlineOptions.ShutdownBreak     == "Unchanged" and 
        oCmdlineOptions.ResetBreak        == "Unchanged" and
        oCmdlineOptions.MachineCheckBreak == "Unchanged"):

        _log.error("\n\n\001ired\001Invalid command line specified") 
        _log.error("\001ired\001All ITP DAL Break cmdline options set to 'Unchanged', so there's nothing to do here!\n") 
        return(0)

    #  Find the thread number of an enabled thread we can use
    nEnabledThread = FindEnabledThread(base_itpii)

    #  If we have no available CPU threads, we're kinda dead in the water
    if ( nEnabledThread == -1 ):
            _log.error("\n\n\001ired\001All CPU threads are reported as invalid or disabled.  This is really bad.  Can't continue.\n") 
            _log.error("\n\001ired\001Check itp.threads[*].isvalid() and isenabled().") 
            _log.error("\001ired\001Make sure they return True for at least one thread in the system.") 
            _log.error("\001ired\001If all threads show up disabled, either you have a really bad CPU,") 
            _log.error("\001ired\001or there's something wrong with the ITP DAL.\n") 
            return(0)

    #  Figure out if we need to change ShutdownBreak
    _log.debug("DEBUG: Evaluating ShutdownBreak status...")
    bModifyingShutdown = evaluateCurrentBreakStatus(oCmdlineOptions.ShutdownBreak, 
                                                    ("%s" % base_itpii.threads[nEnabledThread].cv.shutdownbreak))

    #  Figure out if we need to change ResetBreak
    _log.debug("DEBUG: Evaluating ResetBreak status...")
    bModifyingReset = evaluateCurrentBreakStatus(oCmdlineOptions.ResetBreak,
                                                    ("%s" % base_itpii.threads[nEnabledThread].cv.resetbreak))

    #  Figure out if we need to change MachineCheckBreak
    _log.debug("DEBUG: Evaluating MachineCheckBreak status...")
    bModifyingMachineCheck = evaluateCurrentBreakStatus(oCmdlineOptions.MachineCheckBreak,
                                                    ("%s" % base_itpii.threads[nEnabledThread].cv.machinecheckbreak))

    #  Indicate whether we need to modify any breaks or not
    logIntendedModifications(   base_itpii, 
                                oCmdlineOptions, 
                                bModifyingShutdown,
                                bModifyingReset,
                                bModifyingMachineCheck,
                                nEnabledThread)

    #  In order to modify some ITP DAL breaks, the CPU must go through
    #  a probe-mode transition after setting the control variable in
    #  order to make the break active.   Here, we check for the need to
    #  modify these specific breaks in order to determine if we need to 
    #  execute an itp.halt() or not
    if (bModifyingMachineCheck or bModifyingShutdown):
        bProbeModeNeeded    =   True
        #  Check if system was running before the script started;
        #  flag error if system is currently halted
        if base.isrunning():
            _log.info("System started out in running state.")
        else:
            _log.error("\n\001ired\001System started out in halted state.") 
            _log.error("This script must do a probe-mode exit to make changes")
            _log.error("to some ITP DAL breaks, so it expects the system to be")
            _log.error("running when invoked.")
            _log.error("Not assuming it's ok to do itp.go() on halted system.\n")
            return(0)

    #  Try to do a probe mode transition if we've determined that we need to do so
    if (not bErrorsOccurred and bProbeModeNeeded):
        bHaltSuccess = ValToolsDalUtilities.tryHalt()
        bErrorsOccurred = not bHaltSuccess

    #  If no errors have occurred, then try modifying each of the ITP
    #  DAL breaks that we intend to modify.  Trap any exceptions and
    #  report them to the user
    if (not bErrorsOccurred):
        bModifySuccess = ModifyBreaks(base_itpii, oCmdlineOptions, 
                                      bModifyingShutdown, bModifyingReset,
                                      bModifyingMachineCheck)
        bErrorsOccurred = not bModifySuccess

    # Exit probe mode to return the system to a running state
    # Note:  this actually modifies machinecheckbreak and shutdownbreak
    if (bProbeModeNeeded):
        bGoSuccess = ValToolsDalUtilities.tryGo()
        bErrorsOccurred = not bGoSuccess

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


