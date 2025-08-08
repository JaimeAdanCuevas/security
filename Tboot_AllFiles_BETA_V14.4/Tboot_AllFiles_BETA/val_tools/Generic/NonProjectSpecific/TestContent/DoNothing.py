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
#| $Id: DoNothing.py 176 2015-05-12 21:02:32Z amr\egross $
#| $Date: 2015-05-12 14:02:32 -0700 (Tue, 12 May 2015) $
#| $Author: amr\egross $
#| $Revision: 176 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Script to wait for a specified interval (doing nothing) and print status
    messages periodically during this time.
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
__version__             = "$Rev: 176 $".replace("$Rev:","").replace("$","").strip()
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

    parser.add_option("--duration", action="store", dest="Duration", 
                      type="int", default=60,
                      help="Length of time (seconds) to do nothing (sleep).")


    parser.add_option("--status_interval", action="store", dest="StatusInterval", 
                      type="int", default=0,
                      help="Interval in which to print a status update to the log file indicating process is alive.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  If status interval is not specified, assign default value
    if (oCmdlineOptions.StatusInterval == 0):
        oCmdlineOptions.StatusInterval = int(oCmdlineOptions.Duration/60)
    #  If the value is still zero, make it 1 (applies to really small intervals)
    if (oCmdlineOptions.StatusInterval == 0):
        oCmdlineOptions.StatusInterval = 1

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug          Option read as %s" % oCmdlineOptions.Debug          )
    lLogger.debug("Duration       Option read as %s" % oCmdlineOptions.Duration       )
    lLogger.debug("StatusInterval Option read as %s" % oCmdlineOptions.StatusInterval )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Function Wait for a Specified Duration and Print Regular Status Messages
#|
#|  Inputs:     
#|              Duration to wait
#|              Interval for status update messages to be printed
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def doNothing(nDuration, nStatusInterval):
    nStartTime = _time.time()
    nEndTime   = nStartTime + nDuration
    lLogger.info("I'm going to sit here and do nothing for %d seconds (%d minutes) (%d hours)" % (nDuration, int(nDuration/60), int(nDuration/3600)) )
    lLogger.info("    The time is now:        %s" % _time.strftime("%a, %d %b %Y %H:%M:%S +0000", _time.gmtime(nStartTime)))
    lLogger.info("    I will stop waiting at: %s" % _time.strftime("%a, %d %b %Y %H:%M:%S +0000", _time.gmtime(nEndTime)))
    lLogger.info("")
    lLogger.info("You should see a status message every %d seconds (%d minutes) (%d hours)" % (nStatusInterval, int(nStatusInterval/60), int(nStatusInterval/3600)) )
    if (nDuration < nStatusInterval):
        _time.sleep(nDuration)
    else:
        nInterval = 0
        while (_time.time() < nEndTime):
            _time.sleep(nStatusInterval)
            nInterval += 1
            lLogger.info("    I have completed interval %4d at time: %s" % (nInterval ,_time.strftime("%a, %d %b %Y %H:%M:%S +0000", _time.gmtime())))

    lLogger.info("I'm done waiting now: %s" % _time.strftime("%a, %d %b %Y %H:%M:%S +0000", _time.gmtime()))
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

    #  Function to gracefully do nothing
    bErrorsOccurred = not doNothing(oCmdlineOptions.Duration,  oCmdlineOptions.StatusInterval)

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


