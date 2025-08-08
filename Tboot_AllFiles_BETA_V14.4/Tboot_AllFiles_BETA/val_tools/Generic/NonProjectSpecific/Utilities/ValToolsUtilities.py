#!/usr/bin/env python
############################################################################
# INTEL CONFIDENTIAL
# Copyright 2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corp-
# oration or its suppliers and licensors. The Material may contain trade
# secrets and proprietary and confidential information of Intel Corpor-
# ation and its suppliers and licensors, and is protected by worldwide
# copyright and trade secret laws and treaty provisions. No part of the
# Material may be used, copied, reproduced, modified, published, uploaded,
# posted, transmitted, distributed, or disclosed in any way without
# Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellect-
# ual property right is granted to or conferred upon you by disclosure or
# delivery of the Materials, either expressly, by implication, inducement,
# estoppel or otherwise. Any license under such intellectual property
# rights must be express and approved by Intel in writing.
############################################################################
# $Id: ValToolsUtilities.py 142 2015-03-04 17:44:09Z amr\egross $
# $Date: 2015-03-04 09:44:09 -0800 (Wed, 04 Mar 2015) $
# $Author: amr\egross $
# $Revision: 142 $
############################################################################
# TODO:
#   * Add global constants for PCH device number and DID table
#   * Comments and formatting
############################################################################
## How to Import Me
#
#   # val_tools Utilities Import - gotta find it first!
#   sScriptPath = _os.path.dirname(__file__)
#   if (bDEBUG): 
#       print "ScriptPath:                  %s" % sScriptPath
#   sUtilitiesPath = sScriptPath + "/../Utilities"  #  <--- make sure this is the correct relative path!
#   if (bDEBUG): 
#       print "ValToolsUtilsPath:           %s" % sUtilitiesPath
#   sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
#   if (bDEBUG):
#       print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
#   _sys.path.append(sUtilitiesPath)
#   import ValToolsDalUtilities as _ValToolsDalUtilities
############################################################################

"""
    Library of useful functions that do not use ITP or PythonSV commands
"""

## Standard libary imports
import time         as _time
import logging      as _logging
import subprocess   as _subprocess
import shlex        as _shlex

## Global Variables/Constants


#+----------------------------------------------------------------------------+
#|  Function To Configure Log File And Echo Output To Screen
#|
#|  Sets up the PythonSV logger from the toolbox library,
#|      including setting filename, format, and output verbosity
#|  Sets output level to DEBUG if global DEBUG variable is set; otherwise
#|      sets output level to INFO
#|
#|  Inputs:     
#|              bDebug:         boolean indicating whether we print debug
#|                              output or not
#|              sLogfileName:   text name of file in which to put output
#|  Returns:    
#|              Logger object, lLogger
#|
#+----------------------------------------------------------------------------+
def setupLogger(bDebug, sLogFileName):

    # Logfile name is the script name with the PID appended
    # to distinguish different instances of the script
    lLogger = _logging.getLogger(__name__)

    if bDebug:
        lLogger.setLevel(_logging.DEBUG)
    else:
        lLogger.setLevel(_logging.INFO)

    # Create formatter  e.g. "[   ERROR] This is an error message"
    #     levelname has a width of 8 to accommodate the largest string: CRITICAL
    formatter = _logging.Formatter('[%(levelname)8s] %(message)s')

    # Create console handler 
    #     set formatter to object above
    shConsoleHandler = _logging.StreamHandler()
    shConsoleHandler.setFormatter(formatter)

    # Create log file handler 
    #     set formatter to object above
    fhLogHandler = _logging.FileHandler(sLogFileName, "w")
    fhLogHandler.setFormatter(formatter)

    # Add ConsoleHandler and LogHandler to logger
    lLogger.addHandler(shConsoleHandler)
    lLogger.addHandler(fhLogHandler)


    return lLogger


#+----------------------------------------------------------------------------+
#|  Function To Print Generic Startup Banner
#|
#|  Inputs:     
#|              lLogger:        Logger object
#|              nOutputWidth:   Width, in characters, of screen/file output
#|              sScriptName:    Text name of script being run
#|              sVersion:       Text containing version string for script
#|  Returns:    
#|              1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def printStartupBanner(lLogger, nOutputWidth, sScriptName, sVersion):
    sStartTime = _time.asctime(_time.localtime())
    logDelimiter(lLogger, nOutputWidth)
    lLogger.info(" %s(v%s) started on %s" % (sScriptName, sVersion, sStartTime))
    logDelimiter(lLogger, nOutputWidth)
    return 1


#+----------------------------------------------------------------------------+
#|  Function To Print Generic Finishing Banner
#|
#|  Inputs:     
#|              lLogger:            Logger object
#|              bErrorsOccurred:    indicates whether script was successful
#|              nOutputWidth:       Width, in characters, of screen/file output
#|              sScriptName:        Text name of script being run
#|              sVersion:           Text containing version string for script
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth, sScriptName, sVersion):
    sStatus = "unsuccessfully" if bErrorsOccurred else "successfully"
    sEndTime = _time.asctime(_time.localtime())   
    logDelimiter(lLogger, nOutputWidth)
    lLogger.info(" %s(v%s) finished %s on %s" % (sScriptName, sVersion,
                                              sStatus, sEndTime))
    logDelimiter(lLogger, nOutputWidth)
    return 1


#+----------------------------------------------------------------------------+
#|  Function To Print A Standard-width Delimiter to the Screen/Logfile
#|
#|  Inputs:     
#|              nOutputWidth:    intended width of delimiter, in characters
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def logDelimiter(lLogger, nOutputWidth):
    lLogger.info("=" * nOutputWidth)
    return 1


#+----------------------------------------------------------------------------+
#|  Execute an OS command with error handling and logging
#|
#|  Inputs:     
#|              lLogger:          Logger object
#|              sCommand:         string containing the actual command
#|              sDescription:     short description of what command does
#|              bCriticalStep:    [optional] indicates whether command failure 
#|                                should result in function returning success
#|              bVerbose:         [optional] whether to print command output
#|              bDoNotRun:        [optional] whether to run the command or just 
#|                                print text of what we'd normally do
#|              bCheckReturnCode: [optional] whether running the command is
#|                                enough or if we need a zero return code, too
#|  Returns:    
#|              1 if bCriticalStep is False or command is successful
#|              0 if bCriticalStep is True and command fails (see options above)
#|
#|  Example Usage:
#|
#|  sDescription = "Change all instances of Foo to Bar in somefile"
#|  sCommand     = "sed -i s/Foo/Bar/g /usr/local/etc/somefile"
#|  bSuccess     = _ValToolsUtilities.runOsCommand(sCommand, sDescription, True)
#|  if (not bSuccess):
#|      return 0
#|
#+----------------------------------------------------------------------------+
def runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, 
                 bVerbose=True, bDoNotRun=False, bCheckReturnCode=True):

    bOverallSuccess         = 0 # final function success indicator
    bCommandFailedToRun     = 0 # intermediate indicator for whether the command ran
    bCommandReturnedZero    = 0 # intermediate indicator for command return status

    lLogger.info("Attempting to %s" % sDescription)
    lLogger.info("    Executing command: '%s'" % sCommand)
    
    #  If we're in debug mode, don't actually run the OS command!
    if (bDoNotRun):
        lLogger.info("Not actually executing command because DoNotRun was requested")
        bOverallSuccess = 1
    #  In normal mode, go ahead and run the command as requested
    else:
        sStdoutData =   None
        sStderrData =   None

        #  Attempt to run the command
        try:
            spOsCommand = _subprocess.Popen(_shlex.split(sCommand), 
                                            stdout=_subprocess.PIPE,
                                            stderr=_subprocess.PIPE)
            (sStdoutData, sStderrData) = spOsCommand.communicate() 
        #  If the command failed to run 
        #  (as in an exception, not just returning non-zero exit code)
        except Exception, eOsCommand:
            lLogger.error("    Failed to run command to %s" % sDescription)
            lLogger.error("    Command error: \n\n%s" %eOsCommand)
            if (bCriticalStep):
                lLogger.error("    This is a critical step, so I'm done.")
                bCommandFailedToRun = 1
        #  If the command ran, then attempt to get its output and return code
        else:
            sStdoutData = sStdoutData.rstrip('\n')
            sStderrData = sStderrData.rstrip('\n')
            lLogger.info("    Successfully executed command to %s" % sDescription)
            #  In verbose mode, print all the command output and RC to logger
            if (bVerbose):
                lLogger.info("Command stdout output was:\n\"%s\"\n" % sStdoutData)
                lLogger.info("Command stderr output was:\n\"%s\"\n" % sStderrData)
                if (spOsCommand.returncode == None):
                    lLogger.info("Something bad happened... I didn't get a return code!")
                else:
                   lLogger.info("Command return code was:\"%d\"" % spOsCommand.returncode)
            bCommandFailedToRun     = 0
            bCommandReturnedZero    = (spOsCommand.returncode == 0)

    #  If not a critical step, we always report success
    if (not bCriticalStep):
        bOverallSuccess = 1
        if (bVerbose):
            lLogger.info("CriticalStep not specified, so returning default of success.")
    #  If it is a critical step, we need to look at command results
    else:
        #  If the command didn't run, then that's automatic failure
        if (bCommandFailedToRun):
            lLogger.info("CriticalStep specified and command failed to run; returning failure status.")
            bOverallSuccess = 0
        #  If the command ran, then look at the return code if necessary
        else:
            lLogger.info("CriticalStep specified and command executed;")
            lLogger.info("    success indicated by CheckReturnCode and")
            lLogger.info("    the command's actual return code.")
            bOverallSuccess = (not bCheckReturnCode) or bCommandReturnedZero

    return bOverallSuccess


#+----------------------------------------------------------------------------+
#|  Execute an OS command with error handling and logging, returning its output
#|
#|  Inputs:     
#|              lLogger:        Logger object
#|              sCommand:       string containing the actual command
#|              sDescription:   short description of what command does
#|              bVerbose:       [optional] whether to print command output
#|              bDoNotRun:      [optional] whether to run the command or just 
#|                              print text of what we'd normally do
#|  Returns:    
#|              string containing command output
#|              "returnOsCommand: Command Failure" if command fails
#|
#|  Example Usage:
#|
#|  sDescription = "Change all instances of Foo to Bar in somefile"
#|  sCommand     = "sed -i s/Foo/Bar/g /usr/local/etc/somefile"
#|  sCmdOutput   = _ValToolsUtilities.returnOsCommand(sCommand, sDescription)
#|  if (sCmdOutput == "returnOsCommand: Command Failure"):
#|      return 0
#|
#+----------------------------------------------------------------------------+
def returnOsCommand(lLogger, sCommand, sDescription, 
                 bVerbose=True, bDoNotRun=False):

    sCommandOutput = "CommandNotRun"

    lLogger.info("Attempting to %s" % sDescription)
    lLogger.info("    Executing command: '%s'" % sCommand)

    #  If we're in debug mode, don't actually run the OS command!
    if (bDoNotRun):
        lLogger.info("Not actually executing command because DoNotRun was requested")
        return "Command not actually run because DoNotRun mode requested in function call"
    #  In normal mode, go ahead and run the command as requested
    else:
        try:
            spOsCommand = _subprocess.Popen(_shlex.split(sCommand), stdout=_subprocess.PIPE)
        except Exception, eOsCommand:
            lLogger.error("    Failed to run command to %s" % sDescription)
            lLogger.error("    Command error: \n\n%s" %eOsCommand)
            raise eOsCommand
            return "returnOsCommand: Command Failure"
        else:
            sCommandOutput = spOsCommand.stdout.read().rstrip('\n')
            lLogger.info("    Successfully ran command to %s" % sDescription)
            if (bVerbose):
                lLogger.info("    Command output was:\n\"%s\"" % sCommandOutput)
            return sCommandOutput


