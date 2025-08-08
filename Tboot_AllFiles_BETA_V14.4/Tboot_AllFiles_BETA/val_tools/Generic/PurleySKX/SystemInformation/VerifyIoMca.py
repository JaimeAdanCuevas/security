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
#| $Id: VerifyIoMca.py 203 2015-11-12 22:22:57Z egross $
#| $Date: 2015-11-12 14:22:57 -0800 (Thu, 12 Nov 2015) $
#| $Author: egross $
#| $Revision: 203 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   * Figure out how to make the output from register details go to the log
#|     handler so it's stored in the log file, too!
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
__version__             = "$Rev: 203 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
nDONT_CARE              = -1
nSOCKET_SPECIFIC        = -10
#lSKX_IIO_STACKS         = ("cstack", "pstack0", "pstack1", "pstack2")
# leave out cstack since we don't need to look at that here and it doesn't
# have the mc_ctl2 register, which would complicate the checking logic
lSKX_IIO_STACKS         = ("pstack0", "pstack1", "pstack2")
nSKX_IIO_BUSSES         = 4
sIIO_BUS                = "xxIIO_BUSxx"
sIIO_STACK              = "xxIIO_STACKxx"

# val_tools DAL Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
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

    parser.add_option("--pstack", action="store",
                      type="int", dest="PStack", default=-1,
                      help="Indicates that a valid MCA should be present in the machine check bank for the specified PStack.  Specifying '-1' (default) means no machine checks expected.")

    parser.add_option("--mca_type", action="store", type="choice", 
                      choices=["Fatal", "NonFatal", "None"], dest="McaType", default="None",
                      help="Indicates the severity of the MCA we should see; default is none.  IIO only supports MCEs for uncorrectable errors, so the only other valid choices are Fatal and NonFatal.")

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
    _log.debug("PStack       Option read as %s"  % oCmdlineOptions.PStack        )

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

    # If the expected value is nDONT_CARE, we're just logging the value
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
        #  TODO: figure out out to make the output below go to the log handler
        #  so it's stored in the log file, too!
        socket.uncore0.readregister("%s" % sRegister).show()

    return (not bErrorFound)


#+----------------------------------------------------------------------------+
#|  Populate data structures containing all the register bits to check
#|  properly
#|
#|  Inputs:     
#|
#|  Returns:    
#|              Dictionary of Iio Register fields 
#|
#+----------------------------------------------------------------------------+
def defineExpRegVals(bEnabled, nValidMca, sMcaType):

    # Data structures to keep track of all the registers/fields we need to check
    dictIioBusExpBits = dict()
    dictIioStackExpBits = dict()

    # Create dictionary entries for all registers where we'll be using field
    # in the code below
    # Note:  a value of nDONT_CARE means we'll just log the value, not check it
    dictIioBusExpBits['iio_iiomiscctrl_bxxIIO_BUSxxd05f0'] = dict()
    dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']      = dict()
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl']        = dict()
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl2']       = dict()
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_addr']       = dict()
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']       = dict()
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']     = dict()

    if (bEnabled) :
        dictIioBusExpBits['iio_iiomiscctrl_bxxIIO_BUSxxd05f0']['enable_io_mca']       = 1
        dictIioBusExpBits['iio_iiomiscctrl_bxxIIO_BUSxxd05f0']['enable_pcc_eq0_sev1'] = 0
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev0_map']                 = 1
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev1_map']                 = 0
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev2_map']                 = 0
    else :
        dictIioBusExpBits['iio_iiomiscctrl_bxxIIO_BUSxxd05f0']['enable_io_mca']       = 0
        dictIioBusExpBits['iio_iiomiscctrl_bxxIIO_BUSxxd05f0']['enable_pcc_eq0_sev1'] = 0
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev0_map']                 = 1
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev1_map']                 = 1
        dictIioBusExpBits['iio_sysmap_bxxIIO_BUSxxd05f2']['sev2_map']                 = 1

    if (nValidMca != -1) :
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_val']        = nSOCKET_SPECIFIC
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_over']       = 0
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_uc']         = 1
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_en']         = 1
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_miscv']      = 1
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_addrv']      = 0
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_pcc']        = 1
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_s']          = 1
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_ar']         = 1
        if (sMcaType == "NonFatal"):
            dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_mcacod']     = 0x0E0B
        elif (sMcaType == "Fatal"):
            dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_mcacod']     = 0x0E0B
        else:
            dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_mcacod']     = "Invalid MCA Type Specified"
    else :                                                                   
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_val']        = 0
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_over']       = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_uc']         = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_en']         = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_miscv']      = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_addrv']      = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_pcc']        = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_s']          = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_ar']         = nDONT_CARE
        dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_mcacod']     = nDONT_CARE


    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl']['ucr_nonfatalmcaen']     = 1
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl']['ucr_fatalmcaen']        = 1

    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl2']['mce_ctl']              = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl2']['spare32']              = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl2']['spare30']              = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_ctl2']['spare14_0']            = nDONT_CARE
    
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_addr']['enh_mca_avail']        = nDONT_CARE
    
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['enh_mca_avail_63_40']  = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['ucr_segment_log']      = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['ucr_bus_log']          = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['ucr_device_log']       = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['ucr_function_log']     = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_misc']['enh_mca_avail_15_0']   = nDONT_CARE
    
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_cesi']           = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_cec']            = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_oi']             = nDONT_CARE
    dictIioStackExpBits['iio_xxIIO_STACKxx_mc_status']['ucr_mscod']          = nDONT_CARE

    return(dictIioStackExpBits, dictIioBusExpBits)


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
    (dictIioStackExpBits, dictIioBusExpBits) = defineExpRegVals(oCmdlineOptions.IoMcaEnabled, oCmdlineOptions.ValidMca, oCmdlineOptions.McaType) 
    _log.info("I'm checking the following conditions in your system:")
    _log.info("    IoMca Enabled:         %s" % str(oCmdlineOptions.IoMcaEnabled))
    _log.info("    IoMca Valid:           %s" % str(oCmdlineOptions.ValidMca))
    _log.info("    IoMca PStack:          %s" % str(oCmdlineOptions.PStack))
    _log.info("    IoMca Type:            %s" % str(oCmdlineOptions.McaType))

    # Loop through all sockets available, looking for registers to check
    for socket in sktList:
        _log.info( "=" * nOutputWidth)
        _log.info( ("Details for:  %s" % socket._name.replace("s","S")))

        # Loop through all IIO Stacks on this socket, looking for IIO registers to check
        for sStack in (lSKX_IIO_STACKS): 

            # Loop through all defined registers on this IIO Stack
            for sRegister in sorted(dictIioStackExpBits.keys()) :
                sRegisterInstance = sRegister.replace(sIIO_STACK, sStack)
                _log.info("\n    Register:  %s" % sRegisterInstance)
     
                # Loop through all defined fields in this register
                for sField in sorted(dictIioStackExpBits[sRegister].keys()) :
                    # Determine current and expected values of this register
                    nCurVal = int(socket.uncore0.readregister("%s" % sRegisterInstance).getfieldobject(sField))
                    nExpVal = int(dictIioStackExpBits[sRegister][sField])
     
                    # If we have a socket-specific value, then check the socket number
                    # against the expected socket and set to 1 only if we're processing
                    # the expected socket
                    if (nExpVal == nSOCKET_SPECIFIC) :
                        if (socket._name == "socket%d" % oCmdlineOptions.ValidMca) :
                            nExpVal = 1
                        else:
                            nExpVal = 0

                    # For PStack registers, we only want to check them if we're iterating
                    # over the PStack specified by the user; all others are Don't Care
                    sTargetPStack = "pstack%d" % oCmdlineOptions.PStack
                    if (sStack != sTargetPStack):
                        nExpVal = nDONT_CARE

                    # Inform user if value read matches the expected value
                    if (not checkRegField(nCurVal, nExpVal, sField, sRegisterInstance, socket)):
                        nErrors += 1

        # Loop through all IIO Busses on this socket, looking for IIO registers to check
        for nBus in range(nSKX_IIO_BUSSES): 

            # Loop through all defined registers on this IIO Bus
            for sRegister in sorted(dictIioBusExpBits.keys()) :
                sRegisterInstance = sRegister.replace(sIIO_BUS, str(nBus))
                _log.info("\n    Register:  %s" % sRegisterInstance)
     
                # Loop through all defined fields in this register
                for sField in sorted(dictIioBusExpBits[sRegister].keys()) :
                    # Determine current and expected values of this register
                    nCurVal = int(socket.uncore0.readregister("%s" % sRegisterInstance).getfieldobject(sField))
                    nExpVal = int(dictIioBusExpBits[sRegister][sField])
     
                    # If we have a socket-specific value, then check the socket number
                    # against the expected socket and set to 1 only if we're processing
                    # the expected socket
                    if (nExpVal == nSOCKET_SPECIFIC) :
                        if (socket._name == "socket%d" % oCmdlineOptions.ValidMca) :
                            nExpVal = 1
                        else:
                            nExpVal = 0
                    # Inform user if value read matches the expected value
                    if (not checkRegField(nCurVal, nExpVal, sField, sRegisterInstance, socket)):
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


