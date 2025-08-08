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
#| $Id: SystemErrorCheck.py 194 2015-09-19 01:02:54Z amr\egross $
#| $Date: 2015-09-18 18:02:54 -0700 (Fri, 18 Sep 2015) $
#| $Author: amr\egross $
#| $Revision: 194 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  wrap threads[0] access in try block in case there are no threads
#+----------------------------------------------------------------------------+

"""
    Script to figure out which platform we're using and run the appropriate
    version of syserrs/klaxon/etc. to check for Machine Checks and other
    errors logged in various registers in the CPU/PCH
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import xml.etree.ElementTree as _ElementTree
from optparse import OptionParser

# pythonsv imports
import common.toolbox as _toolbox

# Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 194 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
sDalTopoConfigFilePath  = "C:\Intel\DAL\TopoConfig.xml"

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
import ValToolsUtilities    as _ValToolsUtilities



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

    parser.add_option("--pretest", 
                      action="store_true", dest="PreTestMode", default=False,
                      help="Run this command as part of Automation PreTest phase")

    parser.add_option("--posttest",
                      action="store_true", dest="PostTestMode", default=False,
                      help="Run this command as part of Automation PostTest phase")

    parser.add_option("--force_pass",
                      action="store_true", dest="ForcePass", default=False,
                      help="USE WITH CAUTION!  Script will ignore the result of the \
                            project-specific error checking script and report PASS. \
                            Use this is the project script is broken, but you want to\
                            run it anyway and not fail PreTest steps.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Can't have both --pretest and --posttest
    if (oCmdlineOptions.PreTestMode and oCmdlineOptions.PostTestMode):
        _log.error("\001ired\001Can't specify both --pretest and --posttest at the same time!")
        exit(1)
    #  Inform user if we're running in automation mode
    elif (oCmdlineOptions.PreTestMode or oCmdlineOptions.PostTestMode):
        _log.info("Running %s in automation mode: %s" 
                  % (sScriptName, ("PreTest" if oCmdlineOptions.PreTestMode else "PostTest")))
    #  If not in automation mode, then we're in manual mode
    else:
        _log.info("Running %s in Manual mode" % sScriptName)

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug        Option read as %s" % oCmdlineOptions.Debug         )
    _log.debug("PreTestMode  Option read as %s" % oCmdlineOptions.PreTestMode   )
    _log.debug("PostTestMode Option read as %s" % oCmdlineOptions.PostTestMode  )
    _log.debug("ForcePass    Option read as %s" % oCmdlineOptions.ForcePass     )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Function to Determine Type of Platform Being Used
#|
#|  Gets PlatformType data from ITP DAL TopoConfgi.xml XML file
#|      This file is usually located in c:\Intel\DAL
#|      The format expected is something like this:
#|
#|          <TopoConfig>
#|            <PlatformType Value="HSX_Grantley_ReferenceSettings"/>
#|
#|  Inputs:     None
#|  Returns:    string containing PlatformType extracted from DAL XML file
#|
#+----------------------------------------------------------------------------+
def getPlatformType():
    sPlatformType   = ""

    # Determine if the DAL TopoConfig XML file is available
    if (not _os.path.exists(sDalTopoConfigFilePath)):
        _log.error("\n")
        _log.error("Unable to open the DAL TopoConfig XML file.  I need this file")
        _log.error("    to determine what Platform/CPU we're using.")
        _log.error("    The file I tried to access was:")
        _log.error("    %s" % sDalTopoConfigFilePath)
        _log.error("NOT running System Error Check, as I don't know which one to run!")
        _log.error("\n")
    # If we found the XML file, extract the Platform Type info from it
    else:
        # Read DAL TopoConfig XML file into an Element Tree
        # Find the "PlatformType" element, if it exists
        try:
            tDalTopoConfig = _ElementTree.parse(sDalTopoConfigFilePath)
        #  If the file was bad or otherwise couldn't be read as valid XML,
        #  then we're pretty much done
        except:
            _log.error("\n")
            _log.error("Unable to read XML file:")
            _log.error("    %s" % sDalTopoConfigFilePath)
            _log.error("Either the file is not an XML file or has internal syntax errors.")
            _log.error("This probably means that your ITP DAL is not installed/configured properly.")
            _log.error("\n")
            return sPlatformType
        rDalTopoConfigRoot = tDalTopoConfig.getroot()
        ePlatformType = rDalTopoConfigRoot.find("PlatformType")

        # Make sure we found the "PlatformType" element in the XML
        if (ePlatformType == None):
            _log.error("\n")
            _log.error("There was no 'PlatformType' defined in ITP DAL XML.")
            _log.error("I have no idea what platform/CPU we're using!")
            _log.error("This probably means that your ITP DAL is not installed/configured properly.")
            _log.error("\n")
        # Extract the string that contains the actual platform type    
        else:
            # Check that we can find the "Value" attribute
            sPlatformType = ePlatformType.attrib.get('Value')
            if (sPlatformType == None):
                _log.error("\n")
                _log.error("There was no 'Value' attribute defined for 'PlatformType' in ITP DAL XML.")
                _log.error("I have no idea what platform/CPU we're using!")
                _log.error("This probably means that your ITP DAL is not installed/configured properly.")
                _log.error("\n")
                sPlatformType   = ""
            # Strip off the "_ReferenceSettings" suffix and we have the Platform Type!
            else:
                _log.info("Raw    Platform Type reported by ITP DAL is: '%s'" % sPlatformType)
                # We expect the PlatformType value to look like:
                #    <CPUNAME>_<PLATFORMNAME>_ReferenceSettings
                # We need to make sure that there are at least 3 fields when
                # we split the string using an underscore as a delimiter
                lPlatformType = sPlatformType.split("_")
                # If we have exactly 3 fields, it's easy to determine the platform type
                if (len(lPlatformType) == 3):
                    sPlatformType   = "%s_%s" % (lPlatformType[0], lPlatformType[1])
                # If we have more than 3 fields, make an educated guess at the platform type
                elif (len(lPlatformType) > 3):
                    _log.warn("Possible Invalid Platform Type - Expected 2 underscores, found %d" % (len(lPlatformType) - 1))
                    sPlatformType   = ""
                    # Assume platform type is everything but the part after the last underscore
                    for nElement in range (len(lPlatformType)-2):
                        sPlatformType   = "%s%s_" % (sPlatformType, lPlatformType[nElement])
                    sPlatformType   = "%s%s" % (sPlatformType, lPlatformType[len(lPlatformType)-2])
                # If we have less than 3 fields, that's no good
                else:
                    _log.error("Invalid Platform Type - Expected 2 underscores, found %d" % (len(lPlatformType) - 1))
                    _log.error("    Since there are less than 3 fields, I don't know what to do.")
                    sPlatformType   = "InvalidPlatformTypeFromDalXml"
                _log.info("Parsed Platform Type reported by ITP DAL is: '%s'" % sPlatformType)
    return sPlatformType
    

#+----------------------------------------------------------------------------+
#|  Check That The Platform Config Is Consistent With The Actual Cpu In The System
#|
#|  Reads the "devicetype" from the itp.threads[0].device data structure and 
#|  compares it with the CPU information obtained from the DAL TopoConfig XML
#|  file.  The XML data is formatted like: <CPUtype>_<PlatformType>, and this
#|  CPUtype should match the CPU reported via JTAG from the DAL.
#|  
#|  This step is necessary because the user may configure the DAL's Config
#|  Console incorrectly; thus the CPU/Platform reported in the XML file may
#|  not match the actual CPU/Platform.  This function's purpose is to catch
#|  this inconsistency and allow the user to correct the problem.
#|
#|  Inputs:
#|              string containing the PlatformType (e.g. "HSX_Grantley")
#|  
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def cpuTypeIsValid(sPlatformType):
    bValidCpu = False

    import itpii
    itp = itpii.baseaccess()
    #  Figure out what CPU we have in the system
    sDalCpuName = itp.threads[0].device.devicetype
    _log.info("Detected '%s' CPU as registered by the DAL..." % sDalCpuName) 

    sPlatformTypeCpuName = _re.split("_", sPlatformType)[0]
    _log.info("Detected '%s' CPU in DAL Platform XML file..." % sPlatformTypeCpuName) 

    if (sDalCpuName == sPlatformTypeCpuName):
        _log.info("DAL CPU matches Platform XML CPU, so it appears the DAL is configured properly.") 
        bValidCpu = True
    elif (sDalCpuName == "BDX") and (sPlatformTypeCpuName == "BDXDE"):
        _log.info("Platform XML calls this CPU BDXDE, but the DAL still calls it BDX.") 
        _log.info("This doesn't technically match, but it's ok, and we'll proceed.") 
        bValidCpu = True
    else:
        _log.error("\001ired\001DAL CPU does not match Platform XML CPU.") 
        _log.error("\001ired\001Please check your ITP DAL configuration.") 
        bValidCpu = False

    return bValidCpu

#+----------------------------------------------------------------------------+
#|  Function To Determine Applicable Error Checking Script
#|
#|  This is the meat of this particular script: once we've determined the type
#|  of platform we're using, we need to select the appropriate error checking
#|  script and associated command line arguments.
#|
#|  This function is essentially a big case statement with a section for each
#|  project, where "project" is a combination of Platform and CPU.  The code 
#|  in each section can be as simple or as complicated as necessary, including
#|  adding provisions for different behavior during manual usage vs.
#|  automated PreTest/PostTest or other constraints.
#|
#|  Inputs:     
#|              string containing the PlatformType (e.g. "HSX_Grantley")
#|              datastructure holding command line options
#|
#|  Returns:    string containing command to be run to check for system errors
#|
#+----------------------------------------------------------------------------+
def getProjectSystemErrorCheckCmd(sPlatformType, oCmdlineOptions):
    sCommand = ""

    if   (sPlatformType == "IVT_Brickland"):
        sCommand = "python c:/automation/pythonsv/ivytown/tools/syserrs.py --jc --halt --warn --itpmanualscans"
    elif (sPlatformType == "HSX_Brickland"):
        sCommand = "python c:/automation/pythonsv/haswellx/tools/syserrs.py --jc --halt --warn --itpmanualscans"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "--bootclear")
    elif (sPlatformType == "BDX_Brickland"):
        sCommand = "python c:/automation/pythonsv/broadwellx/tools/syserrs.py --jc --halt --warn --itpmanualscans"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "--bootclear")
    elif (sPlatformType == "HSX_Grantley"):
        sCommand = "python c:/automation/pythonsv/haswellx/tools/syserrs.py --halt --warn --itpmanualscans"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "--bootclear")
    elif (sPlatformType == "BDX_Grantley"):
        sCommand = "python c:/automation/pythonsv/broadwellx/tools/syserrs.py --halt --warn --itpmanualscans"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "--bootclear")
    elif (sPlatformType == "BDXDE_Grangeville"):
        sCommand = "python c:/automation/pythonsv/broadwellx/tools/syserrs.py --halt --warn --itpmanualscans"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "--bootclear")
    elif (sPlatformType == "SKX_LBG_Purley"):
        sCommand = "python c:/automation/pythonsv/falconvalley/tools/syserrs.py --skx"
        if (oCmdlineOptions.PreTestMode):
            sCommand = "%s %s" % (sCommand, "")
    else:
        sCommand = ""

    _log.debug("DEBUG: Error check command: '%s'" % sCommand)

    return sCommand


#+----------------------------------------------------------------------------+
#|  Function To Run Applicable Error Checking Script
#|
#|  Contains provision for DEBUG mode where we just print the command that
#|  would have been run and don't actually run anything.
#|
#|  Inputs:    
#|              string containing command to be run to check for system errors
#|
#|  Returns:    
#|              True if command exited with zero status (success)
#|              False if command exited with non-zero status (failure)
#|
#+----------------------------------------------------------------------------+
def runProjectSystemErrorCheckCmd(sCommand):
    bSuccess = False
    _log.info("Error check command: '%s'" % sCommand)
    try:
        if bDebug:
            _log.result("\n")
            _log.result("\001iyellow\001    DEBUG mode:  not actually running error checking command")
            _log.result("\n")
            bSuccess = True
        else:
            sDescription = "run the project-specific error checking script."
            bSuccess = _ValToolsUtilities.runOsCommand( _log, sCommand, sDescription, 
                                                        bCriticalStep=True, bVerbose=True,
                                                        bDoNotRun=False)
    except Exception, eErrorCheck :
        _log.error("\001ired\001Something bad happened when I tried to run the error checking script!")
        _log.error("       Error: %s" %eErrorCheck)
        return False

    return (bSuccess)



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
    _ValToolsDalUtilities.setupLogger(bDebug, sLogfileName)
    _ValToolsDalUtilities.printStartupBanner(nOutputWidth, 
                                             sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Determine the platform/CPU that we're using
    sPlatformType   = getPlatformType()

    #  If we don't know what platform we have, we don't know what to run!
    if (sPlatformType == ""):
        _log.error("\n")
        _log.error("\001ired\001Unable to detect platform type.  Cannot proceed with error checking.") 
        _log.error("\n")
        bErrorsOccurred = True

    # Check that the platform config is consistent with the actual CPU in the system
    #
    #  NOTE:: bypass this if statement if you want to script to run really fast
    #         otherwise, this part of the script will import ITP commands, which will
    #         make the script take longer
    if (not bErrorsOccurred):
        if (not cpuTypeIsValid(sPlatformType)):
            _log.error("\n")
            _log.error("\001ired\001Detected invalid CPU for '%s' Platform...  Cannot proceed with error checking." % sPlatformType) 
            _log.error("\n")
            bErrorsOccurred = True

    #  If we have a known platform, then we need to run the corresponding error
    #  checking script
    if (not bErrorsOccurred):
       _log.info("Detected '%s' Platform ...  Attempting to run error checking." % sPlatformType) 

       sCommand = getProjectSystemErrorCheckCmd(sPlatformType, oCmdlineOptions)

       if (sCommand == ""):
           _log.error("\n")
           _log.error("Unrecognized Platform type: '%s'!" % sPlatformType)
           _log.error("\001ired\001I don't know which error checking script to run.")
           _log.error("\n")
           bErrorsOccurred = True
       else:
           bErrorCheckPass = runProjectSystemErrorCheckCmd(sCommand)
           if (bErrorCheckPass):
                _log.result("%s project-specific error checking run successfully and passed." % sPlatformType) 
           else:
               _log.error("\n")
               _log.error("\001ired\001%s project-specific error checking exited with non-zero status." % sPlatformType) 
               _log.error("Check the log files for more details.") 
               _log.error("\n")
               bErrorsOccurred = True


    #  If there were errors but the user wants to force a PASS result, warn user
    #  and then change the script result before the final step
    if(bErrorsOccurred and oCmdlineOptions.ForcePass):
        _log.error("\n")
        _log.error("\001ired\001--force_pass specified!  Even though there were errors found,") 
        _log.error("\001ired\001      we'll exit indicating there were no errors.") 
        _log.error("\n")
        bErrorsOccurred = False

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


