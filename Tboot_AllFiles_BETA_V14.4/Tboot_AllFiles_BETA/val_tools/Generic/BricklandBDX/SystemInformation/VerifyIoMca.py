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
#| $Id: VerifyIoMca.py 195 2015-09-21 23:15:35Z amr\egross $
#| $Date: 2015-09-21 16:15:35 -0700 (Mon, 21 Sep 2015) $
#| $Author: amr\egross $
#| $Revision: 195 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  Add code to differentiate CPU type if register names/values change
#+----------------------------------------------------------------------------+

"""
    Write something here that summarizes what this script does
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
from optparse import OptionParser
from common   import colorapi as _colorapi

# pythonsv imports
import common.toolbox    as _toolbox
import components.socket as _sockets

# Global Variables/Constants
bDebug                  = False
bVerbose                = False
nOutputWidth            = 80
__version__             = "$Rev: 195 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
nDONT_CARE              = -1
nSOCKET_SPECIFIC        = -10

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

    parser.add_option("--verbose", action="store_true",
                      dest="Verbose", default=False,
                      help="Turn on Verbose functionality of script (print more stuff).")

    parser.add_option("--enabled", action="store_true",
                      dest="IoMcaEnabled", default=False,
                      help="Indicates that the IOMCA feature should be enabled.")

    parser.add_option("--validmca", action="store",
                      type="int", dest="ValidMca", default=-1,
                      help="Indicates that a valid MCA should be present in the machine check bank on the specified socket.  Specifying '-1' (default) means no machine checks expected.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Set global bVerbose variable and logger mesaging level if necessary
    if (oCmdlineOptions.Verbose):
        global bVerbose
        bVerbose = oCmdlineOptions.Verbose

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug        Option read as %s"  % oCmdlineOptions.Debug           )
    _log.debug("IoMcaEnabled Option read as %s"  % oCmdlineOptions.IoMcaEnabled    )
    _log.debug("ValidMca     Option read as %s"  % oCmdlineOptions.ValidMca        )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Compare expected and current values of a register field and report result
#|
#|  Inputs:     
#|              Current Value (integer)
#|              Expected Value (integer)
#|              Register field name (string)
#|              Register name (string)
#|              Socket we're looking at (socket object)
#|
#|  Returns:    True if values match; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkRegField(nCurVal, nExpVal, sField, sRegister, socket):
    bErrorFound =   False

    # If the expected value is DONT_CARE, we're just logging the value
    if (nExpVal == nDONT_CARE) :
        _colorapi.setFgColor('yellow')
        _log.info("        Current value           (%1x)      LOG ONLY  for: %-30s" % (nCurVal, sField))
        _colorapi.resetColor()
    else:
        # Compare values and inform user
        if (nCurVal == nExpVal) :
            _colorapi.setFgColor('green')
            _log.info("        Current/Expected values (%1x/%1x)     MATCH    for: %-30s" % (nCurVal, nExpVal, sField))
            _colorapi.resetColor()
        else:                                                                                                
            _colorapi.setFgColor('red')
            _log.info("        Current/Expected values (%1x/%1x) DO NOT MATCH for: %-30s" % (nCurVal, nExpVal, sField))
            _colorapi.resetColor()
            bErrorFound = True

    # Print full register contents if verbose option specified
    if bVerbose :
        _log.info("")
        _log.info("        Full details of register:")
        socket.uncore0.readregister("%s" % sRegister).show()

    return (not bErrorFound)


#+----------------------------------------------------------------------------+
#|  Populate data structures containing all the register bits to check
#|  properly
#|
#|  Inputs:     
#|
#|  Returns:    
#|              Dictionary of Uncore Register fields 
#|              Dictionary of QPI Register fields 
#|
#+----------------------------------------------------------------------------+
def defineExpRegVals(bEnabled, nValidMca):

    # Data structures to keep track of all the registers/fields we need to check
    dictUncoreExpBits = dict()
    dictQpiExpBits = dict()

    # Create dictionary entries for all registers where we'll be using field
    # in the code below
    dictUncoreExpBits['iiomiscctrl']      = dict()
    dictUncoreExpBits['pxpd05f2_sysmap']  = dict()
    dictUncoreExpBits['iio_cr_mc_ctl']    = dict()
    dictUncoreExpBits['iio_cr_mc_ctl2']   = dict()
    dictUncoreExpBits['iio_cr_mc_addr']   = dict()
    dictUncoreExpBits['iio_cr_mc_misc']   = dict()
    dictUncoreExpBits['iio_cr_mc_status'] = dict()

    if (bEnabled) :
        dictUncoreExpBits['iiomiscctrl']['enable_io_mca']           = 1
        dictUncoreExpBits['iiomiscctrl']['enable_pcc_eq0_sev1']     = 0
        dictUncoreExpBits['pxpd05f2_sysmap']['sev0_map']            = 1
        dictUncoreExpBits['pxpd05f2_sysmap']['sev1_map']            = 0
        dictUncoreExpBits['pxpd05f2_sysmap']['sev2_map']            = 0
    else :
        dictUncoreExpBits['iiomiscctrl']['enable_io_mca']           = 0
        dictUncoreExpBits['iiomiscctrl']['enable_pcc_eq0_sev1']     = 0
        dictUncoreExpBits['pxpd05f2_sysmap']['sev0_map']            = 1
        dictUncoreExpBits['pxpd05f2_sysmap']['sev1_map']            = 1
        dictUncoreExpBits['pxpd05f2_sysmap']['sev2_map']            = 1

    if (nValidMca != -1) :
        dictUncoreExpBits['iio_cr_mc_status']['ucr_val']            = nSOCKET_SPECIFIC
    else :
        dictUncoreExpBits['iio_cr_mc_status']['ucr_val']            = 0


    dictUncoreExpBits['iio_cr_mc_ctl']['ucr_nonfatalmcaen']     = 1
    dictUncoreExpBits['iio_cr_mc_ctl']['ucr_fatalmcaen']        = 1

    dictUncoreExpBits['iio_cr_mc_ctl2']['mce_ctl']              = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_ctl2']['spare32']              = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_ctl2']['spare30']              = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_ctl2']['spare14_0']            = nDONT_CARE
    
    dictUncoreExpBits['iio_cr_mc_addr']['enh_mca_avail']        = nDONT_CARE
    
    dictUncoreExpBits['iio_cr_mc_misc']['enh_mca_avail_63_40']  = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_misc']['ucr_segment_log']      = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_misc']['ucr_bus_log']          = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_misc']['ucr_device_log']       = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_misc']['ucr_function_log']     = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_misc']['enh_mca_avail_15_0']   = nDONT_CARE
    
    dictUncoreExpBits['iio_cr_mc_status']['ucr_over']           = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_uc']             = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_en']             = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_miscv']          = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_addrv']          = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_pcc']            = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_s']              = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_ar']             = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_cesi']           = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_cec']            = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_oi']             = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_mscod']          = nDONT_CARE
    dictUncoreExpBits['iio_cr_mc_status']['ucr_mcacod']         = nDONT_CARE

    return(dictUncoreExpBits, dictQpiExpBits)


#+----------------------------------------------------------------------------+
#|  Check all register bits necessary to confirm that IoMca is enabled
#|  properly
#|
#|  Inputs:     Script command line options
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkIoMca(oCmdlineOptions):
    nErrors = 0
    sktList = _sockets.getAll()

    # Define data structures to keep track of all the registers/fields
    # we need to check.  The expected values in this structure come
    # from the command line arguments specified by the user
    (dictUncoreExpBits, dictQpiExpBits) = defineExpRegVals(oCmdlineOptions.IoMcaEnabled, oCmdlineOptions.ValidMca)
    _log.info("I'm checking the following conditions in your system:")
    _log.info("    IoMca Enabled:         %s" % str(oCmdlineOptions.IoMcaEnabled))
    _log.info("    IoMca Valid:           %s" % str(oCmdlineOptions.ValidMca))

    # Loop through all sockets available, looking for registers to check
    for socket in sktList:
        _log.info( "=" * nOutputWidth)
        _log.info( ("Details for:  %s" % socket._name.replace("s","S")))

        # Loop through all defined registers on this socket
        for sRegister in sorted(dictUncoreExpBits.keys()) :
            _log.info("\n    Register:  %s" % sRegister)

            # Loop through all defined fields in this register
            for sField in sorted(dictUncoreExpBits[sRegister].keys()) :
                # Determine current and expected values of this register
                nCurVal = int(socket.uncore0.readregister("%s" % sRegister).getfieldobject(sField))
                nExpVal = int(dictUncoreExpBits[sRegister][sField])

                # If we have a socket-specifi value, then check the socket number
                # against the expected socket and set to 1 only if we're processing
                # the expected socket
                if (nExpVal == nSOCKET_SPECIFIC) :
                    if (socket._name == "socket%d" % oCmdlineOptions.ValidMca) :
                        nExpVal = 1
                    else:
                        nExpVal = 0
                # Inform user if value read matches the expected value
                if (not checkRegField(nCurVal, nExpVal, sField, sRegister, socket)):
                    nErrors += 1

        # Loop through all QPI ports on this socket, looking for QPI registers to check
        for nPort in range(3):  # where can we get 3 programatically?  Number of QPI ports...

            # Loop through all defined registers for this QPI port
            for sRegister in sorted(dictQpiExpBits.keys()) :
                sFullRegName = "qpi%d_%s" % (nPort, sRegister)
                _log.info("\n    Register:  %s" % sFullRegName)

                # Loop through all defined fields in this register
                for sField in sorted(dictQpiExpBits[sRegister].keys()) :
                    nCurVal = int(socket.uncore0.readregister("%s" % sFullRegName).getfieldobject(sField))
                    nExpVal = int(dictQpiExpBits[sRegister][sField])

                    # Inform user if value read matches the expected value
                    if (not checkRegField(nCurVal, nExpVal, sField, sFullRegName, socket)):
                        nErrors += 1

    _log.info( "=" * nOutputWidth)
    _log.result("I found %d errors while checking registers related to IoMca." % nErrors)
    return (nErrors == 0)


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

    #  Meat of script
    bErrorsOccurred = not checkIoMca(oCmdlineOptions)

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


