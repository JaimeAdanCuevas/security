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
#| Date:05/17/2017
#| Author:Vanila Reddy
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
__version__             = "$Rev: 173 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()

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
import skylakex.ras.general_tools as _T


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
                      dest="FuseCheckout", default=False,
                      help="")



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
    _log.debug("FuseCheckout Option read as %s"  % oCmdlineOptions.FuseCheckout    )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|
#|
#+----------------------------------------------------------------------------+
def checkRegField(nCurVal, nExpVal, sField, sRegister, socket):
    bErrorFound =   False
    # Compare values and inform user
    if (nCurVal == nExpVal) :
        _colorapi.setFgColor('green')
        _log.info("        Current/Expected values (%1x/%1x)     MATCH    for: %-30s" % (nCurVal, nExpVal, sField))
        _colorapi.resetColor()
    else:
        _colorapi.setFgColor('red')
        _log.info("        Current/Expected values (%1x/%1x) DO NOT MATCH for: %-30s" % (nCurVal, nExpVal, sField))
       # _log.error("        There was mismatch in this fuse %s" % sField)
        _colorapi.resetColor()
        bErrorFound = True

    # Print full register contents if verbose option specified
    if bVerbose :
        _log.info("")
        _log.info("        Full details of register:")
        socket.uncore0.readregister("%s" % sRegister).show()

    return (not bErrorFound)


#+----------------------------------------------------------------------------+
#|Compare expected and current values of a register field bits for Security Integration
#| Validation
#|
#|  Inputs:
#|              Registers and the fuse name and expected value
#|
#|  Returns:    Compares and returns true if it matches .
#+----------------------------------------------------------------------------+
def defineExpRegVals(bEnabled=True):

    # Data structures to keep track of all the registers/fields we need to check
    dictcoreExpBits = dict()

    # Create dictionary entries for all registers where we'll be using field
    # in the code below
    dictcoreExpBits['pcu_cr_core_configuration_0']      = dict()
    dictcoreExpBits['pcu_cr_capid0_cfg']               = dict()

    if (bEnabled) :
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['smx_dis']                     = 0
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['lt_sx_en']                    = 1  # Should be enabled for LT_SX capability
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['fit_boot_dis']                = 0
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['production_part']             = 0
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['vmx_dis']                     = 0
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['anchor_cove_en']              = 1 # Should be enabled for BootGuard validation
        dictcoreExpBits['pcu_cr_core_configuration_0']     ['pfat_disable']                = 0 # Should be disabled for BiosGuard validation
        dictcoreExpBits['pcu_cr_capid0_cfg']              ['lt_production']               = 1

    return(dictcoreExpBits)


#+----------------------------------------------------------------------------+
#|
#|
#|  Inputs:     Script command line options
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def FuseCheckout(oCmdlineOptions):
    nErrors = 0
    sktList = _T.get_pysv_sockets()

    # Define data structures to keep track of all the registers/fields
    # we need to check.  The expected values in this structure come
    # from the command line arguments specified by the user
    (dictcoreExpBits) = defineExpRegVals(oCmdlineOptions.FuseCheckout)
    _log.info("I'm checking the following conditions in your system:")
    _log.info("  FuseCheckout :         %s" % str(oCmdlineOptions.FuseCheckout))


    # Loop through all sockets available, looking for registers to check
    for socket in sktList:
        _log.info( "=" * nOutputWidth)
        _log.info( ("Details for:  %s" % socket._name.replace("s","S")))


        # Loop through all defined registers on this socket
        for sRegister in (dictcoreExpBits) :
            _log.info("\n    Register:  %s" % sRegister)

            # Loop through all defined fields in this register
            for sField in sorted(dictcoreExpBits[sRegister].keys()) :
                # Determine current and expected values of this register
                nCurVal = int(socket.uncore0.readregister("%s" % sRegister).getfieldobject(sField))
                nExpVal = int(dictcoreExpBits[sRegister][sField])

                # Inform user if value read matches the expected value
                if (not checkRegField(nCurVal, nExpVal, sField, sRegister, socket)):
                    nErrors += 1



    _log.info( "=" * nOutputWidth)
    _log.result("I found %d errors while checking registers related to TXT-FuseCheckout." % nErrors)
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
    bErrorsOccurred = not FuseCheckout(oCmdlineOptions)

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



