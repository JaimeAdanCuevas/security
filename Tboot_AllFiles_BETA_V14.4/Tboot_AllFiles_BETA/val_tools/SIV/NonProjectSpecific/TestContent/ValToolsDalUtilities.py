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
#| $Id: ValToolsDalUtilities.py 119 2015-02-02 21:25:12Z amr\egross $
#| $Date: 2015-02-02 13:25:12 -0800 (Mon, 02 Feb 2015) $
#| $Author: amr\egross $
#| $Revision: 119 $
#+----------------------------------------------------------------------------+
#| TODO:
#|       * Add global constants for PCH device number and DID table
#|       * Comments and formatting
#+----------------------------------------------------------------------------+
#| How to Import Me
#|
#|  # val_tools Utilities Import - gotta find it first!
#|  sScriptPath = _os.path.dirname(__file__)
#|  if (bDEBUG): 
#|      print "ScriptPath:                  %s" % sScriptPath
#|  sUtilitiesPath = sScriptPath + "/../Utilities"  #  <--- make sure this is the correct relative path!
#|  if (bDEBUG): 
#|      print "ValToolsUtilsPath:           %s" % sUtilitiesPath
#|  sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
#|  if (bDEBUG):
#|      print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
#|  _sys.path.append(sUtilitiesPath)
#|  import ValToolsDalUtilities as _ValToolsDalUtilities
#+----------------------------------------------------------------------------+

"""
    Library of useful functions to interact with the ITP DAL from 
    a Python script
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import time              as _time

# pythonsv imports
import common.toolbox    as _toolbox
import common.baseaccess as _baseaccess 
import itpii             as _itpii

# Global Variables/Constants
bDebug                  = False
__version__             = "$Rev: 119 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
_itp                 = _itpii.baseaccess()
_log                 = _toolbox.getLogger()
_base                = _baseaccess.getglobalbase()



#+----------------------------------------------------------------------------+
#|  Function To Configure Log File And Echo Output To Screen
#|
#|  Sets up the PythonSV logger from the toolbox library,
#|      including setting filename, format, and output verbosity
#|  Sets output level to DEBUG if global DEBUG variable is set; otherwise
#|      sets output level to INFO
#|
#|  Inputs:     None
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def setupLogger(bDebug, sLogFileName):

    # Logfile name is the script name with the PID appended
    # to distinguish different instances of the script
    _log.setFile(sLogFileName)
    _log.setFileFormat('simple')
    if bDebug:
        _log.setFileLevel(_toolbox.DEBUG)
    else:
        _log.setFileLevel(_toolbox.INFO)

    # Configure logger to ouput information to the screen, too
    if bDebug:
        _log.setConsoleLevel(_toolbox.DEBUG)
    else:
        _log.setConsoleLevel(_toolbox.INFO)
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
def LogDelimiter(nOutputWidth):
    _log.info("=" * nOutputWidth)
    return 1



#+----------------------------------------------------------------------------+
#|  Function To Print Generic Startup Banner
#|
#|  Inputs:     None
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def printStartupBanner(nOutputWidth, sScriptName, sVersion):
    sStartTime = _time.asctime(_time.localtime())
    LogDelimiter(nOutputWidth)
    _log.info(" %s(v%s) started on %s" % (sScriptName, sVersion, sStartTime))
    LogDelimiter(nOutputWidth)
    return 1


#+----------------------------------------------------------------------------+
#|  Function To Print Generic Finishing Banner
#|
#|  Inputs:     
#|              bErrorsOccurred:    indicates whether script was successful
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def printFinishingBanner(bErrorsOccurred, nOutputWidth, sScriptName, sVersion):
    sStatus = "unsuccessfully" if bErrorsOccurred else "successfully"
    sEndTime = _time.asctime(_time.localtime())   
    LogDelimiter(nOutputWidth)
    _log.info(" %s(v%s) finished %s on %s" % (sScriptName, sVersion,
                                              sStatus, sEndTime))
    LogDelimiter(nOutputWidth)
    return 1








## Function to Halt CPU threads and report success/failure
def tryHalt():
    _log.info("Trying to halt...\n")
    try:
        _itp.halt()
    except Exception, eHalt :
        _log.error("\n\001ired\001ERROR: ITP halt command failed.")
        _log.error("       ITP error: %s" %eHalt)
        return 0
    else:
        _log.result("\001igreen\001ITP Halt Successful\n\001igreen\001")
        return 1


## Function to Un-Halt CPU threads and report success/failure
def tryGo():
    _log.info("\nTrying to return the processors to running state...\n")
    try :
        _itp.go()
    except Exception, eGo :
        _log.error("\001ired\001ERROR: ITP go command failed.")
        _log.error("       ITP error: %s" %eGo)
        return 0
    else :
        _log.result("\001igreen\001itp.go() succesful!")
        return 1

# Function to read the PCH's VID
def readPchVid():
    nPchVid = -1

    try:
        nPchVid = _base.pcicfg(bus=0, dev=31, fnc=0, reg=0, size=2)
    except Exception, eCfgRd :
        _log.error("\n\001ired\001ERROR: ITP DAL failed to read config register!.")
        _log.error("       ITP error: %s" %eCfgRd)

    return nPchVid


## Function to read the PCH's DID
def readPchDid():
    nPchDid = -1

    try:
        nPchDid = _base.pcicfg(bus=0, dev=31, fnc=0, reg=2, size=2)
    except Exception, eCfgRd :
        _log.error("\n\001ired\001ERROR: ITP DAL failed to read config register!.")
        _log.error("       ITP error: %s" %eCfgRd)

    return nPchDid


## Function to figure out which PCH is in the system
#    Example:
#        sPchType = getPchType()
#        _log.info("PCH Type Detected: %s" % sPchType)
def getPchType():
    sPchType          = "Unknown"
    bWasRunning       = _base.isrunning()
    nPchVid           = -1         # VendorID for PCH
    nPchDid           = -1         # DeviceID for PCH
    bErrorEncountered = False

    # Check to see if we're already halted; we must be halted
    # to be able to do Config Register accesses from the CPU
    if (bWasRunning):
        bHaltSuccess = ValToolsDalUtilities.tryHalt()
        if (not bHaltSuccess):
            _log.error("Since we were unable to halt successfully, we can't read registers.")
            bErrorEncountered = True
    
    #  Assuming no previous errors, we're halted and we can try to
    #  read the Vendor ID (VID) of the PCH
    if (not bErrorEncountered):
        nPchVid = readPchVid()
        _log.debug("Read PCH VID register value: '0x%4x'" % nPchVid) 

    if (nPchVid == -1):
        _log.error("Reading PCH VID failed.... unable to continue")
        bErrorEncountered = True

    #  Assuming no previous errors, we're halted and we can try to
    #  read the Device ID (DID) of the PCH
    if (not bErrorEncountered):
        nPchDid = readPchDid()
        _log.debug("Read PCH DID register value: '0x%4x'" % nPchDid)

    if (nPchDid == -1):
        _log.error("Reading PCH DID failed.... unable to continue")
        bErrorEncountered = True

    #  If we were not halted at the beginning of the script and
    #  we halted successfully during the script, we need to exit probe mode
    #  (a.k.a. "go" or unhalt)
    if (bWasRunning and (not bEncounteredErrors)):
        bGoSuccess = ValToolsDalUtilities.tryGo()
        if (not bGoSuccess):
            _log.error("Since we were unable to unhalt successfully, we can't continue.")
            bErrorEncountered = True

    #  Now use the PCH's VID and DID to determine what platform we're using
    if not(nPchVid == 0x8086):
        _log.error("Unknown PCH Vendor ID (VID):  '0x%4x'" % nPchVid)
        _log.info("I only know about 0x8086, which corresponds to 'Intel'")
    else:
        # Note: PCH DID information can be found in the PCH's C-Spec
        #       under the section on "PCI devices and functions
        #       This is chapter 6 for Patsburg and Wellsburg
        if   (nPchDid & 0xFFF0 == 0x8D40):      # Wellsburg
            sPchType = "WBG"
        elif (nPchDid & 0xFFF0 == 0x1D40):      # Patsburg
            sPchType = "PBG"
        elif (nPchDid & 0xFFF0 == 0x8C40):      # LynxPoint
            sPchType = "LPT"
        else:
            _log.error("Unknown PCH Device ID (DID):  '0x%4x'" % nPchDid)

    _log.debug("PCH Type Detected: %s" % sPchType)
    return sPchType

## Function to figure out what platform we're using
#   Example:
#       #  Use the CPU and PCH types to determine the platform type
#       sPlatformType = evalPlatformType(sCpuType, sPchType)
#       _log.info("Platform Type Detected: %s" % sPlatformType)

def evalPlatformType(sCpuType, sPchType):
    sPlatformType = "Unknown"

    if   (sPchType == "PBG"):
        if   (sCpuType == "IVT"):
            sPlatformType = "BricklandIvt"
        if   (sCpuType == "HSX"):
            sPlatformType = "BricklandHsx"
        elif (sCpuType == "BDX"):
            sPlatformType = "BricklandBdx"
    elif   (sPchType == "WBG"):
        if   (sCpuType == "HSX"):
            sPlatformType = "GrantleyHsx"
        elif (sCpuType == "BDX"):
            sPlatformType = "GrantleyBdx"

    _log.debug("platform Type Detected: %s" % sPlatformType)
    return sPlatformType

