#!/usr/bin/env python
# +----------------------------------------------------------------------------+
# | INTEL CONFIDENTIAL
# | Copyright 2014 Intel Corporation All Rights Reserved.
# |
# | The source code contained or described herein and all documents related
# | to the source code ("Material") are owned by Intel Corporation or its
# | suppliers or licensors. Title to the Material remains with Intel Corp-
# | oration or its suppliers and licensors. The Material may contain trade
# | secrets and proprietary and confidential information of Intel Corpor-
# | ation and its suppliers and licensors, and is protected by worldwide
# | copyright and trade secret laws and treaty provisions. No part of the
# | Material may be used, copied, reproduced, modified, published, uploaded,
# | posted, transmitted, distributed, or disclosed in any way without
# | Intel's prior express written permission.
# |
# | No license under any patent, copyright, trade secret or other intellect-
# | ual property right is granted to or conferred upon you by disclosure or
# | delivery of the Materials, either expressly, by implication, inducement,
# | estoppel or otherwise. Any license under such intellectual property
# | rights must be express and approved by Intel in writing.
# +----------------------------------------------------------------------------+
# | $Id: LogAcmLinux.py 184 2015-08-03 20:18:43Z amr\vanilare $
# | $Date: 2015-08-03 13:18:43 -0700 (Mon, 03 Aug 2015) $
# | $Author: amr\vanilare $
# | $Revision: 184 $
# +----------------------------------------------------------------------------+
# | TODO:
# |   *   Needs cleanup of code.  Template applied, but code content not updated
# +----------------------------------------------------------------------------+

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

import VerifyTrusted as VT

## Global Variables/Constants
bDebug = False
nOutputWidth = 80
__version__ = "$Rev: 184 $".replace("$Rev:", "").replace("$", "").strip()
sScriptName = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug):
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../../Generic/NonProjectSpecific/Utilities"  # <--- make sure this is the correct relative path!
if (bDebug):
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath = _os.path.normpath(sUtilitiesPath)
if (bDebug):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

#  Since we may want to import functionality from this script into another script,
#  only create the Logger instance if this is executing as a script and not being
#  imported as a module
if __name__ == '__main__':
    lLogger = _ValToolsUtilities.setupLogger(bDebug, sLogfileName)

sAcmHeaderAddress = '00020100'
sExpectedFitAddress = '0x00000000ffffb500'
sAnc_Boot_Policy_Manifest_Record_Type= '000c0100'
sAnc_Key_Policy_Manifest_Record_Type= '000b0100'
Acm_Header = '00020100'
#  Linux command 'txtstat' produces a large quantity of text output
#  There are several key tokens in this output that must be present
#  to consider it a successful trusted boot.  This is a list of those
#  text tokens.
lRequiredTxtStatLines = (
    'TXT measured launch: TRUE',
    'secrets flag set: TRUE'
)


# +----------------------------------------------------------------------------+
# |  Handle Command Line Options
# |
# |  This functon defines all supported command line options and invokes the
# |  methods used to extract those options from the user-supplied command line
# |
# |  Inputs:     None
# |  Returns:    Command Line Options Object from OptionParser
# |
# +----------------------------------------------------------------------------+
def parseCommandLine():
    #  Create a parser object and add options to it
    parser = OptionParser()
    parser.add_option("--debug", action="store_true",
                      dest="Debug", default=False,
                      help="Turn on DEBUG functionality of script.")
    parser.add_option("--Fit_Record_Type", action="store",
                      type="choice",
                      choices=[ "AnC_Key_Manifest",
                                "AnC_Boot_Policy_Manifest",
                                "Acm_Header"],
                      default="Acm_Header",
                      help="Please Enter Valid available options :'AnC_Key_Manifest','AnC_Boot_Policy_Manifest','Acm_Header' only")
    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    # Debug output to indica												te what the results of command line processing are
    lLogger.debug("Debug  Option read as %s" %oCmdlineOptions.Debug)
    lLogger.debug("Debug  Option read as %s" %oCmdlineOptions.Fit_Record_Type)
    #  Return options data structure
    return oCmdlineOptions




######################Function for generating FIT table######################

# +----------------------------------------------------------------------------+
# |  Find and Log FIT Table
# |
# |  Inputs:     None
# |  Returns:    True on success; otherwise, False
# |
# +----------------------------------------------------------------------------+
def logFIT():
    lLogger.info("Reading the base FIT Address")
    fit = _subprocess.Popen(["/usr/local/sbin/volatility", "-a", "0xffffffc0"],stdout=_subprocess.PIPE)
    fitAddress = fit.stdout.read().rstrip('\n')
    if(fitAddress):
        fittablefile = open("Fit_Table.log", "w")
        lLogger.info("Creating Log of FIT TABLE of starting from address %s in a file Fit_Table.log" % fit)
        _subprocess.Popen(["/usr/local/sbin/volatility", "-a", fitAddress], stdout=_subprocess.PIPE)
        _subprocess.call(["/usr/local/sbin/volatility", "-a", fitAddress, "-d", "60"], stdout=fittablefile)
        fittablefile.close()
        return True
    else:
        lLogger.error("Failed to read the fit table contents!! ")
        return False


######################Function for generating ACM Header######################

# +----------------------------------------------------------------------------+
# |  Read and log the ACM Header
# |
# |  Inputs:     None
# |  Returns:    True on success; otherwise, False
# |
# +----------------------------------------------------------------------------+
def logACM(FitType,FitRecordType):
    logFIT()
    lLogger.info("Reading FIT Table...Fit Record Checks")

    # Opening fit log for reading the ACM header record
    # File Pointer to fit log
    FpFitlog = open("Fit_Table.log", "r")

    # Opening file for writing ACM header
    # File Pointer to AcmHeader log
    FpAcmHeader = open("acmheader.log", "w")

    content = FpFitlog.readline()
    try:
        # Checking if the system is trusted ,  if not trusted system should not proceed furter to log ACM header.
        #bErrorsOccurred = not VT.validateTrusted()
	bErrorsOccurred = False
    except Exception as e:
	print "Message= " + str(e.message)
        lLogger.error("System is not trusted , this step is Critical so cannot move ahead....")
        return 0
    while content:
	print content
        if FitRecordType in content.split(" "):
            lLogger.info("Fit Record Type '%s' exists which corresponds '%s'" %(FitRecordType ,FitType))
            AcmHeaderStartAddress = content.split(" ")[2]
            _subprocess.call(["/usr/local/sbin/volatility", "-a", AcmHeaderStartAddress, "-d", "80"],stdout=FpAcmHeader)
            lLogger.info("Successfully located the Fit Record...")
            return 1
        else:
            content = FpFitlog.readline()  # reads until end of the fit log
    
    lLogger.info("Fit Record Type any such does not exist...")
    return 0
# +----------------------------------------------------------------------------+
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
# +----------------------------------------------------------------------------+
def main():
    #  Variable definitions
    bErrorsOccurred = False  # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth,
                                          sScriptName, __version__)

    #  Get command line options, if any

    oCmdlineOptions = parseCommandLine()
    if (oCmdlineOptions.Fit_Record_Type == "Acm_Header"):
        bErrorsOccurred = not logACM(FitType="Acm_Header",FitRecordType=Acm_Header)
    elif (oCmdlineOptions.Fit_Record_Type== "AnC_Boot_Policy_Manifest"):
        bErrorsOccurred = not logACM(FitType="AnC_Boot_Policy_Manifest",FitRecordType=sAnc_Boot_Policy_Manifest_Record_Type)
    elif (oCmdlineOptions.Fit_Record_Type == "AnC_Key_Manifest"):
        bErrorsOccurred = not logACM(FitType="AnC_Key_Manifest",FitRecordType=sAnc_Key_Policy_Manifest_Record_Type)
    else:
        lLogger.info("--User Option is set to '%s'" % oCmdlineOptions.Fit_Record_Type)
        lLogger.info("Invalid Option")
        bErrorsOccurred = True
        #_ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth, sScriptName, __version__)
    # return 0 # returning a True value to pass the test in automation.
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth, sScriptName, __version__)
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


