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
#| $Id: CheckPcrs.py 145 2015-03-06 00:56:52Z amr\egross $
#| $Date: 2015-03-05 16:56:52 -0800 (Thu, 05 Mar 2015) $
#| $Author: amr\egross $
#| $Revision: 145 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  The untrusted check can probably be improved to check not just for a
#|      non-match on PCR17 and PCR18, but also that those PCRs actually return
#|      all 0xFF values.
#+----------------------------------------------------------------------------+

"""
    Script compares current PCR register values with previously logged values
    This script takes a logfile containing logged PCR values as INPUT

    From the ACM Writer's Guide:
    --------------------------------------------------
    PCR0 contains the static root of trust measurement, as well as BIOS code
    measurements. These measurements cannot be spoofed because they are rooted
    in hardware. The validity of PCR1-PCR7 rests on the validity of PCR0.
    That is, PCR1-PCR7 can only be trusted if the PCR0 measurement is known
    to be good.  PCR0 - CRTM, BIOS, and Host Platform Extensions

    SINIT code detects whether any of modules in system is NPW, if any of
    modules in system is detected to be NPW, SINIT code extends PCR 17 and 18
    with random values. This prevents possible use of these PCRs for unsealing
    of OS secrets. 
    --------------------------------------------------

    TPM stores measurements in Platform Configuration Registers (PCRs)
    Platform elements of the trusted computing base (TCB), such as SINIT
    and launch control policy (LCP) are put into PCR 17 

    The MLE is extended into PCR 18

    Based on the above information, this script will expect:
    *   PCR0 will always retain its value from boot to boot; any changes
        in this register's value will signal a failure
    *   PCR17 and PCR18 will be expected to retain their values when used
        with PW (production worthy) firmware, just like the check for PCR0.
        However, when NPW (non-production-worthy) firmware is used, they 
        will be expected to have random (different) values from boot to
        boot, and retaining their values from boot to boot will be considered
        a failure.
    *   Debug firmware will have the same expected behavior as PW for these
        three PCRs

"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
import filecmp      as _filecmp
import subprocess   as _subprocess
import shlex        as _shlex
from optparse import OptionParser

## Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 145 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
sUntrustedPcr17         = "PCR-17: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF "
sUntrustedPcr18         = "PCR-18: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF "

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

    parser.add_option("--input_file", action="store", dest="InputFile", 
                      type="string", default="",
                      help="Path and name of file used as input for comparison with current PCR values.")

    parser.add_option("--check_pw", action="store_true",
                      dest="ProductionWorthyCheck", default=False,
                      help="Indicates whether we're checking production-worthy firmware or not. PCRs have different behavior for different FW revisions.")

    parser.add_option("--check_npw", action="store_true",
                      dest="NonProductionWorthyCheck", default=False,
                      help="Indicates whether we're checking non-production-worthy firmware or not. PCRs have different behavior for different FW revisions.")

    parser.add_option("--check_debug", action="store_true",
                      dest="DebugCheck", default=False,
                      help="Indicates whether we're checking debug firmware or not. PCRs have different behavior for different FW revisions.")

    #  Process the actual command line and split it into options and arguments
    parser.add_option("--check_untrusted", action="store_true",
                      dest="UntrustedCheck", default=False,
                      help="Indicates if we've booted untrusted and want to check PCRs. PCRs have different behavior for trusted vs. untrusted boots.")

    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Must have input file specified
    if oCmdlineOptions.InputFile == "":
        lLogger.error("Must specifiy --input_file")
        _sys.exit(1)

    #  Ensure that at least one check is specified
    if (    (not oCmdlineOptions.ProductionWorthyCheck)
        and (not oCmdlineOptions.NonProductionWorthyCheck)
        and (not oCmdlineOptions.DebugCheck)
        and (not oCmdlineOptions.UntrustedCheck)):
        lLogger.error("No checks specified.  One and only one check is required!")
        _sys.exit(1)

    #  Figuring out how many checks the user specified
    #  Python has the capability to treat booleans as '1' or '0',
    #  so we can just add them
    nTotalChecksSpecified =     oCmdlineOptions.ProductionWorthyCheck   \
                            + oCmdlineOptions.NonProductionWorthyCheck  \
                            + oCmdlineOptions.DebugCheck                \
                            + oCmdlineOptions.UntrustedCheck
    lLogger.debug("Total checks specified was: %d" % nTotalChecksSpecified)

    #  Ensure that we only have one type of check specified
    if (nTotalChecksSpecified > 1):
        lLogger.error("Multiple checks specified.  Since some of them conflict with each other, this is an invalid choice.")
        lLogger.info("ProductionWorthyCheck    Option read as %s"  % oCmdlineOptions.ProductionWorthyCheck   )
        lLogger.info("NonProductionWorthyCheck Option read as %s"  % oCmdlineOptions.NonProductionWorthyCheck)
        lLogger.info("DebugCheck               Option read as %s"  % oCmdlineOptions.DebugCheck              )
        lLogger.info("UntrustedCheck           Option read as %s"  % oCmdlineOptions.UntrustedCheck          )
        _sys.exit(1)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug                    Option read as %s"  % oCmdlineOptions.Debug                   )
    lLogger.debug("InputFile                Option read as %s"  % oCmdlineOptions.InputFile               )
    lLogger.debug("ProductionWorthyCheck    Option read as %s"  % oCmdlineOptions.ProductionWorthyCheck   )
    lLogger.debug("NonProductionWorthyCheck Option read as %s"  % oCmdlineOptions.NonProductionWorthyCheck)
    lLogger.debug("DebugCheck               Option read as %s"  % oCmdlineOptions.DebugCheck              )
    lLogger.debug("UntrustedCheck           Option read as %s"  % oCmdlineOptions.UntrustedCheck          )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Function to check the values of PCRs 00, 17, and 18
#|
#|  Inputs:     
#|              oCmdlineOptions : data structure containing command line args
#|
#|  Returns:    1 if true; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def pcrsAreValid(oCmdlineOptions):
    #  Initialize variables to use later
    bAllPcrChecksOk = False
    bDoneChecking   = False
    sPrevPcr00Value = ""
    sPrevPcr17Value = ""
    sPrevPcr18Value = ""
    sCurPcr00Value  = ""
    sCurPcr17Value  = ""
    sCurPcr18Value  = ""

    #  Get previous PCR values from the user-specified input file
    (sPrevPcr00Value, sPrevPcr17Value, sPrevPcr18Value) = getPrevPcrValues(oCmdlineOptions)
    if oCmdlineOptions.UntrustedCheck:
        lLogger.info("NOTE: Untrusted Check specified")
        lLogger.info("      Will compare PCR17 and PCR18 to static expected values rather than their")
        lLogger.info("      previous values.")

    #  Make sure we got values for all PCRs
    if (sPrevPcr00Value == "" or  sPrevPcr17Value == "" or sPrevPcr18Value == ""):
        lLogger.error("Unable to get one or more of the previous values for the PCRs.")
        lLogger.error("See above output for details.")
        bDoneChecking = True

    #  Get current PCR values from a file in /sys/devices/ 
    if not bDoneChecking:
        lLogger.info('Getting Current Values of PCR registers.......')
        (sCurrPcr00Value, sCurrPcr17Value, sCurrPcr18Value) = getCurrPcrValues()

        #  Make sure we got values for all PCRs
        if (sCurrPcr00Value == "" or  sCurrPcr17Value == "" or sCurrPcr18Value == ""):
            lLogger.error("Unable to get one or more of the current values for the PCRs.")
            lLogger.error("See above output for details.")
            bDoneChecking = True



    #  Compare the current and previous/expected values of all PCRs
    if not bDoneChecking:
        bPcr00ValuesMatch   = pcrMatch(sPrevPcr00Value, sCurrPcr00Value)

        #  Special processing for Untrusted - we expect PCR 17 and 18
        #  to return a special value always, so no comparison to previous
        #  values is necessary
        if oCmdlineOptions.UntrustedCheck:
            bPcr17ValuesMatch   = pcrMatch(sUntrustedPcr17, sCurrPcr17Value)
            bPcr18ValuesMatch   = pcrMatch(sUntrustedPcr18, sCurrPcr18Value)
        else:
            bPcr17ValuesMatch   = pcrMatch(sPrevPcr17Value, sCurrPcr17Value)
            bPcr18ValuesMatch   = pcrMatch(sPrevPcr18Value, sCurrPcr18Value)


        #  Report match results to help with debug - make sure reader
        #  understands what the inputs to the checks are
        lLogger.info("Comparing Current and Previous/Expected Values for Relevant PCRs:")
        lLogger.info("    PCR00 Match: %s" % bPcr00ValuesMatch)
        lLogger.info("    PCR17 Match: %s" % bPcr17ValuesMatch)
        lLogger.info("    PCR18 Match: %s" % bPcr18ValuesMatch)
     
        #  Production Worthy FW Checks
        if oCmdlineOptions.ProductionWorthyCheck:
            lLogger.info("Performing Production-Worthy (PW) Checks")
            bAllPcrChecksOk  = bPcr00ValuesMatch and bPcr17ValuesMatch and bPcr18ValuesMatch
            lLogger.info("    PCR00 Check: %s" % bPcr00ValuesMatch)
            lLogger.info("    PCR17 Check: %s" % bPcr17ValuesMatch)
            lLogger.info("    PCR18 Check: %s" % bPcr18ValuesMatch)
     
        #  Non-Production-Worthy FW Checks
        if oCmdlineOptions.NonProductionWorthyCheck:
            lLogger.info("Performing Non-Production-Worthy (NPW) Checks")
            bAllPcrChecksOk  = bPcr00ValuesMatch and (not bPcr17ValuesMatch) and (not bPcr18ValuesMatch)
            lLogger.info("    PCR00 Check: %s" %      bPcr00ValuesMatch )
            lLogger.info("    PCR17 Check: %s" % (not bPcr17ValuesMatch))
            lLogger.info("    PCR18 Check: %s" % (not bPcr18ValuesMatch))
     
        #  Debug FW Checks
        if oCmdlineOptions.DebugCheck:
            lLogger.info("Performing Debug Checks")
            bAllPcrChecksOk  = bPcr00ValuesMatch and bPcr17ValuesMatch and bPcr18ValuesMatch
            lLogger.info("    PCR00 Check: %s" % bPcr00ValuesMatch)
            lLogger.info("    PCR17 Check: %s" % bPcr17ValuesMatch)
            lLogger.info("    PCR18 Check: %s" % bPcr18ValuesMatch)

        #  Untrusted Checks
        if oCmdlineOptions.UntrustedCheck:
            lLogger.info("Performing Untrusted Checks")
            bAllPcrChecksOk  = bPcr00ValuesMatch and bPcr17ValuesMatch and bPcr18ValuesMatch
            lLogger.info("    PCR00 Check: %s" % bPcr00ValuesMatch)
            lLogger.info("    PCR17 Check: %s" % bPcr17ValuesMatch)
            lLogger.info("    PCR18 Check: %s" % bPcr18ValuesMatch)

    return bAllPcrChecksOk


#+----------------------------------------------------------------------------+
#|  Retrieve previous PCR values from specified file
#|
#|  Inputs:     
#|              oCmdlineOptions : data structure containing command line args
#|
#|  Returns:    List of 3 PCR values in order (i.e. 00, 17, 18)
#|
#+----------------------------------------------------------------------------+
def getPrevPcrValues(oCmdlineOptions):
    sPcr00Value =   ""
    sPcr17Value =   ""
    sPcr18Value =   ""

    #  Get previous PCR values from the user-specified input file
    lLogger.info('Getting Previous Values of PCR registers from file:')
    lLogger.info("    %s" % oCmdlineOptions.InputFile)

    #  Maybe wrap this file open command in a try/except block?
    with open(oCmdlineOptions.InputFile, 'r') as fPcrsFile:
        sPcrData = fPcrsFile.readlines()

        #  Loop through the lines of the input file, searching for 
        #  the three PCRs we're interested in
        for sLine in sPcrData:
            lLogger.debug("    %s" % sLine.rstrip('\n'))
            if _re.match("PCR-00", sLine):
                sPcr00Value = sLine.rstrip('\n')
            if _re.match("PCR-17", sLine):
                sPcr17Value = sLine.rstrip('\n')
            if _re.match("PCR-18", sLine):
                sPcr18Value = sLine.rstrip('\n')

    #  Inform user what we found
    lLogger.info("PCR00 Text:  '%s'" % sPcr00Value)
    lLogger.info("PCR17 Text:  '%s'" % sPcr17Value)
    lLogger.info("PCR18 Text:  '%s'" % sPcr18Value)

    return (sPcr00Value, sPcr17Value, sPcr18Value)


#+----------------------------------------------------------------------------+
#|  Retrieve current PCR values from Linux filesystem access method
#|
#|  Inputs:     None
#|
#|  Returns:    List of 3 PCR values in order (i.e. 00, 17, 18)
#|
#+----------------------------------------------------------------------------+
def getCurrPcrValues():
    sPcr00Value =   ""
    sPcr17Value =   ""
    sPcr18Value =   ""

    #  Find the Linux file that contains the values of all the PCRs
    lLogger.info("    Trying to find the PCRs within the Linux filesystem...") 
    sCommand        = "find /sys/devices/ -name pcrs"
    sPcrsFilename   = "ThisIsNotAFile"

    #  Debug mode skips trying to find the file in the Linux filesystem
    if (bDebug):
        sPcrsFilename   = "./current_pcrs.txt"
    #  Open the output of the Linux 'find' command to get the location of the file
    else:
        try:
            spIoRead = _subprocess.Popen(_shlex.split(sCommand), stdout=_subprocess.PIPE)
        except Exception, ePopen:
            lLogger.error("OS command to find the PCRs file failed.")
            lLogger.error("Command was: '%s'" % sCommand)
            lLogger.error("Failure Details: '%s'" % ePopen)
            lLogger.error("This is a critical step, so I can't continue...")
            return 0
        else:
            sPcrsFilename = spIoRead.stdout.read().rstrip('\n')
            lLogger.info("Successfully ran command to find PCRs file.")
            lLogger.info("    PCRs file determined to be %s" % sPcrsFilename)


    #  Read the Linux file that contains the values of all the PCRs
    lLogger.info('    Getting Current Values of PCR registers from file:')
    lLogger.info("    %s" % sPcrsFilename)

    #  Maybe wrap this file open command in a try/except block?
    with open(sPcrsFilename, 'r') as fPcrsFile:
        sPcrData = fPcrsFile.readlines()

        #  Loop through the lines of the input file, searching for 
        #  the three PCRs we're interested in
        for sLine in sPcrData:
            lLogger.debug("    %s" % sLine.rstrip('\n'))
            if _re.match("PCR-00", sLine):
                sPcr00Value = sLine.rstrip('\n')
            if _re.match("PCR-17", sLine):
                sPcr17Value = sLine.rstrip('\n')
            if _re.match("PCR-18", sLine):
                sPcr18Value = sLine.rstrip('\n')

    #  Inform user what we found
    lLogger.info("PCR00 Text:  '%s'" % sPcr00Value)
    lLogger.info("PCR17 Text:  '%s'" % sPcr17Value)
    lLogger.info("PCR18 Text:  '%s'" % sPcr18Value)

    return (sPcr00Value, sPcr17Value, sPcr18Value)


#+----------------------------------------------------------------------------+
#|  Function to compare two PCR values
#|
#|  Inputs:     two strings containing PCR values to compare
#|  Returns:    True if values match; otherwise, False
#|
#+----------------------------------------------------------------------------+
def pcrMatch (sPrevValue, sCurValue):
    bValuesMatch = False
    if (sPrevValue == sCurValue):
        lLogger.info("    Current and Expected PCR values match:")
        lLogger.info("        Current  : '%s'" % sCurValue)
        lLogger.info("        Expected : '%s'" % sPrevValue)
        bValuesMatch = True
    else:
        lLogger.info("    Current and Expected PCR values DO NOT match:")
        lLogger.info("        Current  : '%s'" % sCurValue)
        lLogger.info("        Expected : '%s'" % sPrevValue)
        bValuesMatch = False

    return bValuesMatch




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
    bValuesValid         = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Check the PCR values
    bValuesValid =   pcrsAreValid(oCmdlineOptions)

    #  Print out result
    if (bValuesValid):
        lLogger.info("PCR values determined to be valid:  PASS")
    else:
        lLogger.error("PCR values determined to be invalid:  FAIL")

    #  Return boolean indicating whether we were successful or not
    _ValToolsUtilities.printFinishingBanner(lLogger, not bValuesValid, nOutputWidth,
                                            sScriptName, __version__)
    return (bValuesValid)
    

####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


