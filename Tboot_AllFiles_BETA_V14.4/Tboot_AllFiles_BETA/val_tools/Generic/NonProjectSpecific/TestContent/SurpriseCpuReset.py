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
#| $Id: SurpriseCpuReset.py 162 2015-04-23 00:17:52Z amr\egross $
#| $Date: 2015-04-22 17:17:52 -0700 (Wed, 22 Apr 2015) $
#| $Author: amr\egross $
#| $Revision: 162 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Script to cause warm reset via either:
        * Port write to 0xCF9 via ITP DAL access
        * ITP DAL 'resettarget()' command
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
from optparse import OptionParser

# pythonsv imports
import common.toolbox as _toolbox
import itpii          as _itpii

# Global Variables/Constants
bDebug                  = 0
nOutputWidth            = 80
__version__             = "$Rev: 162 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
_itp                    = _itpii.baseaccess()

# val_tools DAL Utilities Import - gotta find it first!
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


    parser.add_option("--resettarget", action="store_true",
                      dest="ResetTarget", default=False,
                      help="Use itp.resettarget() instead of port write to initiate reset.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug        Option read as %s"  % oCmdlineOptions.Debug        )
    _log.debug("ResetTarget  Option read as %s"  % oCmdlineOptions.ResetTarget  )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Write a value of 0x6 to IO Port 0xCF9
#|
#|  See PCH documentation of register 0xCF9
#|  for more details.
#|
#|      itp.threads[0].port(0xCF9,0x06) 
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def writeResetRegister():
    _log.result("Attempting Port 0xCF9 write...")
    try :
        _itp.threads[0].port(0xCF9,0x06) 
    except Exception, ePortCF9 :
        _log.error("\001ired\001ERROR: Write to Port 0xCF9 failed.")
        _log.error("       ITP error: %s" %ePortCF9)
        return False
    else :
        _log.result("\001igreen\001Port 0xCF9 write succesful!")

    return True


#+----------------------------------------------------------------------------+
#|  Reset the system via a write to the PCH reset register at 0xCF9
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def resetViaRegisterWrite():
    bWasRunning = False
    bErrorsOccurred = False

    #  Halt CPUs if they're running
    if not _itp.cv.isrunning :
        _log.result("CPUs detected already halted; not attempting to halt again...")
    else :
        bWasRunning = True
        if not _ValToolsDalUtilities.tryHalt() :
            _log.error("\n\001ired\001Unable to Halt CPU.  This is really bad...")
            bErrorsOccurred = True

    #  Write the reset register to cause reset
    if (not bErrorsOccurred):
        bErrorsOccurred = (not writeResetRegister())
    #  Othewise, check to see if the system was originally running and 
    #  return it to its previous state if so
    else:
        if (bWasRunning):
            _ValToolsDalUtilities.tryGo()
    return (not bErrorsOccurred)


#+----------------------------------------------------------------------------+
#|  Reset the system the DAL command "resettarget"
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def resetViaResetTarget():

    try :
        _log.info("Attempting to run ITP DAL 'resettarget()' command")
        _itp.resettarget() 
    except Exception, eResetTarget :
        _log.error("\001ired\001ERROR: ITP DAL 'resettarget' command failed.")
        _log.error("       ITP DAL error: %s" %eResetTarget)
        return False
    else :
        _log.result("\001igreen\001ITP DAL ResetTarget succesful!")

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
    bWasRunning     = True  # used to indicate whether the system was halted when the script was started

    #  Startup tasks - get the logger configured
    _ValToolsDalUtilities.setupLogger(bDebug, sLogfileName)
    _ValToolsDalUtilities.printStartupBanner(nOutputWidth, 
                                             sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Implement the requested reset
    if (oCmdlineOptions.ResetTarget == True):
        bErrorsOccurred = (not resetViaResetTarget())
    else:
        bErrorsOccurred = (not resetViaRegisterWrite())

    #  Write the reset register to cause reset
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


