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
#| $Id: InjectErrorWheaHct.py 170 2015-04-29 20:09:26Z amr\egross $
#| $Date: 2015-04-29 13:09:26 -0700 (Wed, 29 Apr 2015) $
#| $Author: amr\egross $
#| $Revision: 170 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Basic script to inject errors via WHEA HCT tool - hardcoded for now;
    can be expanded later
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
__version__             = "$Rev: 170 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

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

    parser.add_option("--errorcmd", action="store",
                      dest="ErrorCmd", default="/verbose /cap",
                      help="Command options to give to wheahct.exe.  See wheahct help for list of valid options.")

    parser.add_option("--delay", action="store",
                      dest="Delay", type='int', default=30,
                      help="Delay (in seconds) before executing WheaHct.exe command.")

    parser.add_option("--wheahct_path", action="store",
                      dest="WheahctPath", default="c:/wheahct",
                      help="Location of wheahct.exe executable.")

    parser.add_option("--duration", action="store",
                      dest="Duration", type='int', default=0,
                      help="Specifies duration (in seconds) of error injection.  Default of '0' means single injection.")

    parser.add_option("--interval", action="store",
                      dest="Interval", type='int', default=0,
                      help="Specifies interval (in seconds) between multiple injections.  Default of '0' means as fast as possible.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug       Option read as %s"  % oCmdlineOptions.Debug        )
    lLogger.debug("Delay       Option read as %s"  % oCmdlineOptions.Delay        )
    lLogger.debug("ErrorCmd    Option read as %s"  % oCmdlineOptions.ErrorCmd     )
    lLogger.debug("WheahctPath Option read as %s"  % oCmdlineOptions.WheahctPath  )
    lLogger.debug("Duration    Option read as %s"  % oCmdlineOptions.Duration     )
    lLogger.debug("Interval    Option read as %s"  % oCmdlineOptions.Interval     )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Run the WheaHCT tool with the command line option(s) specified
#|
#|  Inputs:     
#|              String to pass to WheaHCT.exe
#|              Path to location of wheahct.exe executable
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def runWheaHct(sErrorCmd, sWheahctPath):
    bSuccess = False

    sCommand = "%s/wheahct.exe %s" % (sWheahctPath, sErrorCmd)
    lLogger.debug("Command was: %s" % sCommand)
    sDescription = "run WHEAHCT.exe with option(s) '%s'" % sErrorCmd
    bSuccess = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                bCriticalStep=True, bVerbose=True,
                                                bDoNotRun=False)
    if not bSuccess:
        return False
    else:
        return True

#+----------------------------------------------------------------------------+
#|  Run the WheaHCT tool with the command line option(s) specified
#|
#|  Inputs:     
#|              String to pass to WheaHCT.exe
#|              Delay (in sec) to wait before executing WheaHCT.exe
#|              Path to location of wheahct.exe executable
#|              Duration of error injection (minutes)
#|              Interval between error injections (seconds)
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def injectErrors(sErrorCmd, nDelay, sWheahctPath, nDuration, nInterval):
    bSuccess = False

    lLogger.info("Waiting %d sec before starting error injection ..." % nDelay)
    _time.sleep(nDelay)

    lLogger.info("Injecting first error ...")
    bSuccess = runWheaHct(sErrorCmd, sWheahctPath)

    nStartTime = _time.time()
    nEndTime   = nStartTime + nDuration

    nErrorCount = 1
    while (bSuccess and (_time.time() < nEndTime)):
        nErrorCount += 1

        lLogger.info("Injecting error (total: %9d) ..." % nErrorCount)
        bSuccess = runWheaHct(sErrorCmd, sWheahctPath)

        lLogger.info("Waiting %d sec before next error injection ..." % nInterval)
        _time.sleep(nInterval)

    if not bSuccess:
        return False
    else:
        return True


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

    #  Run WHEA Hardware Compliance Test (wheahct.exe)
    bErrorsOccurred = not injectErrors(
                                         oCmdlineOptions.ErrorCmd, 
                                         oCmdlineOptions.Delay,
                                         oCmdlineOptions.WheahctPath,
                                         oCmdlineOptions.Duration,
                                         oCmdlineOptions.Interval,
                      )

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


