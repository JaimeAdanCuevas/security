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
#| $Id: VerifyUntrusted.py 136 2015-02-03 00:52:09Z amr\egross $
#| $Date: 2015-02-02 16:52:09 -0800 (Mon, 02 Feb 2015) $
#| $Author: amr\egross $
#| $Revision: 136 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Scripts Verifies the system is booted Untrusted
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
__version__             = "$Rev: 136 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../../Generic/NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
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

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

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
#|  
#|
#|  Inputs:     None
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def validateUntrusted():
    bErrorsOccurred = False
    sCommand="/usr/local/sbin/txt-stat"
    content=_subprocess.Popen(_shlex.split(sCommand),stdout=_subprocess.PIPE)
    output=content.stdout.read()
    stat1='TXT measured launch: FALSE'
    stat2='secrets flag set: FALSE'

    if stat1 not in output:
        lLogger.error("TXTSTAT does not report 'TXT measured launch' to be FALSE")
        bErrorsOccurred = True

    if stat2 not in output:
        lLogger.error("TXTSTAT does not report 'secrets flag set' to be FALSE")
        bErrorsOccurred = True

    # Check exists - add better comment later
    fp_exists=open("lt_exists.log","w")
    sCommand="/usr/local/sbin/volatility -a 0xfed30010"
    exists=_subprocess.Popen(_shlex.split(sCommand),stdout=_subprocess.PIPE)
    _subprocess.call(_shlex.split(sCommand), stdout=fp_exists)
    exist=exists.communicate()[0].rstrip('\n')
    lLogger.info("Checking LT_exists...")
    if exist == 0x0000000000000000:
        lLogger.error("Platform is not LT-strapped.")
	lLogger.error("LT_exists value equal to  0x0000000000000000")
        bErrorsOccurred = True
    else:
	lLogger.info("System passes LT_exists check...")
    # Check joins - add better comment later
    	fp_joins=open("lt_joins.log","w")
    	sCommand="/usr/local/sbin/volatility -a 0xfed30020"
    	joins=_subprocess.Popen(_shlex.split(sCommand),stdout=_subprocess.PIPE)
    	_subprocess.call(_shlex.split(sCommand),stdout=fp_joins)
    	join=joins.communicate()[0].rstrip('\n')
    	lLogger.info("Checking lt_joins...")
	if join != '0x0000000000000000':
        	lLogger.error("CPU's indicating they have joined MLE ")
		lLogger.error("LT_ Joins not equal to 0x0000000000000000")
    		bErrorsOccured = True
	else:
		lLogger.info("LT_Joins as expected value '0x0000000000000000'")
		lLogger.info("System pass LT_joins check.....")
    lLogger.debug("bErrorsOccurred Value: %d" % bErrorsOccurred)

    if (bErrorsOccurred):
        lLogger.error("One or more Untrusted Boot checks failed......")
        lLogger.error("    Check above error messages for details.")
        return(0)
    else:
        lLogger.info("\t\tVerified.......UnTrusted Boot Confirmed!")
        return(1)




#+------------------------------------------------------------------------------+
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

    #  
    bErrorsOccurred = not validateUntrusted()
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


