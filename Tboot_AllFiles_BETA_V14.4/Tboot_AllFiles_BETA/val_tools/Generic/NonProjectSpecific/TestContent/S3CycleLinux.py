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
#| $Id: S3CycleLinux.py 79 2014-12-10 18:50:21Z amr\egross $
#| $Date: 2014-12-10 10:50:21 -0800 (Wed, 10 Dec 2014) $
#| $Author: amr\egross $
#| $Revision: 79 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Script to initiate and log an S3 cycle in Linux and log command output
    as possible.  This script uses the "rtcwake" command to enter S3.
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
bDEBUG              = 0
nOutputWidth        = 80
__version__         = "$Rev: 79 $".replace("$Rev:","").replace("$","").strip()
sScriptName         = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName        = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDEBUG): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../Utilities"  #  <--- make sure this is the correct relative path!
if (bDEBUG): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDEBUG):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

lLogger        = _ValToolsUtilities.setupLogger(bDEBUG, sLogfileName)


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
    parser.add_option("--sleeptime", action="store", dest="SleepTime", 
                      type="int", default=120,
                      help="Time (seconds) to stay in S3 before waking up")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("SleepTime Option read as %s" % oCmdlineOptions.SleepTime)

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Enter S3 and wait a while
#|
#|  Inputs:     nSleepTime:  seconds to stay in S3 before waking
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def doS3Cycle(nSleepTime):
    sCommand    = "/usr/sbin/rtcwake --verbose --auto --mode mem --seconds %d" % nSleepTime

    # Attempt to enter S3
    try:
        lLogger.info("Attempting to enter S3 via command:")
        lLogger.info("    %s" % sCommand)
        spRtcWake = _subprocess.Popen(_shlex.split(sCommand), stdout=_subprocess.PIPE,
                                      stderr=_subprocess.STDOUT)
    # Inform user if unsuccessful; print debug information
    except Exception, ePopen:
        lLogger.error("OS command to enter S3 failed.")
        lLogger.error("Command was: '%s'" % sCommand)
        lLogger.error("Failure Details: '%s'" % ePopen)
        lLogger.error("This is a critical step, so I can't continue...")
        return 0
    # Inform user if successful and log command output
    else:
        lLogger.info("Successfully ran command to enter S3.")
        lLogger.info("Command (rtcwake) Output\n" + spRtcWake.communicate()[0])
    return 1

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

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Meat of script
    doS3Cycle(oCmdlineOptions.SleepTime)

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


