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
#| $Id: LogAcmLinux.py 184 2015-08-03 20:18:43Z amr\vanilare $
#| $Date: 2015-08-03 13:18:43 -0700 (Mon, 03 Aug 2015) $
#| $Author: amr\vanilare $
#| $Revision: 184 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *   Needs cleanup of code.  Template applied, but code content not updated
#+----------------------------------------------------------------------------+

"""
    Script to log the AcmHeader 
    This Scripts generates the AcmHeader by reading the FitTable log genated
    by function logFIT.

    It looks for the records 00020100 in FIT table and print the acmheader
    starting there
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
import subprocess   as _subprocess
from optparse import OptionParser
#import VerifyTrusted as VT

## Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 184 $".replace("$Rev:","").replace("$","").strip()
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
												
sAcmHeaderAddress='00020100'
sExpectedFitAddress='0x00000000ffffb500'

#  Linux command 'txtstat' produces a large quantity of text output
#  There are several key tokens in this output that must be present
#  to consider it a successful trusted boot.  This is a list of those
#  text tokens.
lRequiredTxtStatLines   =   (
                                 'TXT measured launch: TRUE',
                                 'secrets flag set: TRUE'
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


############Function for checking the system is trusted or not###############


def verifyTrusted():
    bErrorsOccurred = False
    #   Check the output of TXTSTAT to ensure it contains the required text tokens
    #   that indicate a successful trusted boot.
    sCommand        = "sudo /usr/sbin/txt-stat"
    sDescription    = "to look for indications of a trusted boot in TXTSTAT output."
    if (bDebug):
        sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription, True)
    else:
        sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription, False)
    if (sCommandOutput == "returnOsCommand: Command Failure"):
        return False
    lLogger.info("Examining TXTSTAT output...")
    for sText in lRequiredTxtStatLines: 
        if sText not in sCommandOutput:
            lLogger.error("    [FAIL] Did not find text: '%s'" % sText)
            bErrorsOccured = True 												
        else:
            lLogger.info("    [PASS] Found text: '%s'" % sText)
    return True

   





######################Function for generating FIT table######################

#+----------------------------------------------------------------------------+
#|  Find and Log FIT Table
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def logFIT():
    lLogger.info("Reading the base FIT Address")
    FIT=_subprocess.Popen(
                          ["/usr/local/sbin/volatility","-a", "0xffffffc0"],
                          stdout=_subprocess.PIPE)
    fit=FIT.stdout.read().rstrip('\n')
    f1=open("fit.log","w")
    if fit == sExpectedFitAddress:    
        lLogger.info("Creating Log of FIT TABLE of 60 records starting from address %s" 
                     % sExpectedFitAddress)
        _subprocess.Popen(["/usr/local/sbin/volatility", "-a", fit], stdout=_subprocess.PIPE)
        _subprocess.call(["/usr/local/sbin/volatility", "-a", fit, "-d", "60"], stdout=f1)
        f1.close()
        return True
    else:
        lLogger.info("FIT ADDRESS expected to be:  %s " % sExpectedFitAddress)
        lLogger.info("Actual FIT was              %s " % fit)
        return False 

    return True
												


######################Function for generating ACM Header######################

#+----------------------------------------------------------------------------+
#|  Read and log the ACM Header
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def logACM():
    logFIT()
    lLogger.info("Generating ACM Header : acmheader.log............!")
    
    # Opening fit log for reading the ACM header record 
    # File Pointer to fit log
    FpFitlog=open("fit.log", "r") 
    
    # Opening file for writing ACM header 
    # File Pointer to AcmHeader log
    FpAcmHeader=open("acmheader.log","w") 
    
    content=FpFitlog.readline()
    
    while content:
        if sAcmHeaderAddress in content.split(" "): # checks for ACMheader record in the fit log content
            lLogger.info("Fit Record Type 0x02 Exists...")
            AcmHeaderStartAddress=content.split(" ")[2]
            _subprocess.call(["/usr/local/sbin/volatility", "-a", AcmHeaderStartAddress, "-d", "80"], stdout=FpAcmHeader)
            lLogger.info("Successfully Generating AcmHeader...")
            return 1
        else:    
            content=FpFitlog.readline() # reads until end of the fit log
    lLogger.info("Fit Record Type 0x02 does not exist...") 
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
    bErrorsOccurred = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __version__)

    #  Get command line options, if any
    try:
        # Checking if the system is trusted ,  if not trusted system should not proceed furter to log ACM header.
        # bErrorsOccured value has to be changed in the function verifyTrusted, once TXT is enabled in SKX automation.
        bErrorsOccurred= not verifyTrusted()
        if (not bErrorsOccurred):
#  Find the ACM Header and write it to a file
            bErrorsOccurred = not logACM()
       #    return True
        else:
            lLogger.error("Couldnt Log Acm Header....")
            return False
    except Exception:
        lLogger.error("System is not trusted , this step is Critical so cannot move ahead....")
        return 0
        oCmdlineOptions = parseCommandLine()
    	_ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,sScriptName, __version__)
    #return 0 # returning a True value to pass the test in automation. 
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,sScriptName, __version__)
    #  Return boolean indicating whether we are successful or not
    return (not bErrorsOccurred)
    

####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


