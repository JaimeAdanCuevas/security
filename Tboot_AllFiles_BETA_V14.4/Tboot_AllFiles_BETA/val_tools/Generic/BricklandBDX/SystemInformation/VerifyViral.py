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
#| $Id: VerifyViral.py 200 2015-10-13 18:02:15Z amr\egross $
#| $Date: 2015-10-13 11:02:15 -0700 (Tue, 13 Oct 2015) $
#| $Author: amr\egross $
#| $Revision: 200 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  Add code to differentiate CPU type if register names/values change
#+----------------------------------------------------------------------------+

"""
    Checks the current state of the registers associated with the Viral mode
    of error containment.  User can specify if Viral is to be enabled/disabled
    and whether the State or Status bits are to be set/cleared.
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
__version__             = "$Rev: 200 $".replace("$Rev:","").replace("$","").strip()
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
                      dest="ViralEnabled", default=False,
                      help="")

    parser.add_option("--state", action="store_true",
                      dest="ViralState", default=False,
                      help="")

    parser.add_option("--status", action="store_true",
                      dest="ViralStatus", default=False,
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
    _log.debug("ViralEnabled Option read as %s"  % oCmdlineOptions.ViralEnabled    )
    _log.debug("ViralState   Option read as %s"  % oCmdlineOptions.ViralState      )
    _log.debug("ViralStatus  Option read as %s"  % oCmdlineOptions.ViralStatus     )

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
def defineExpRegVals(bEnabled=True, bStateAsserted=False, bStatusAsserted=False):

    # Data structures to keep track of all the registers/fields we need to check
    dictUncoreExpBits = dict()
    dictQpiExpBits = dict()

    # Create dictionary entries for all registers where we'll be using field
    # in the code below
    dictUncoreExpBits['pxpd05f2_viral']      = dict()
    dictUncoreExpBits['viral_control']       = dict()
    dictQpiExpBits   ['qpiviral']            = dict()

    if (bEnabled) :
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_global_viral_mask']           = 1
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_signal_global_fatal']         = 0  # If IOMCA is disabled, this will be cleared
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_fatal_viral_alert_enable']    = 1
        dictUncoreExpBits['viral_control']      ['viral_log_disable']               = 0
        dictQpiExpBits   ['qpiviral']           ['qpi_fatal_viral_alert_enable']    = 1
        dictQpiExpBits   ['qpiviral']           ['qpi_signal_global_fatal']         = 1
        dictQpiExpBits   ['qpiviral']           ['qpi_global_viral_mask']           = 1
    else :
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_global_viral_mask']           = 0
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_signal_global_fatal']         = 0  # If IOMCA is disabled, this will be cleared
        dictUncoreExpBits['pxpd05f2_viral']     ['iio_fatal_viral_alert_enable']    = 0
        dictUncoreExpBits['viral_control']      ['viral_log_disable']               = 0
        dictQpiExpBits   ['qpiviral']           ['qpi_fatal_viral_alert_enable']    = 0
        dictQpiExpBits   ['qpiviral']           ['qpi_signal_global_fatal']         = 0
        dictQpiExpBits   ['qpiviral']           ['qpi_global_viral_mask']           = 0



    if (bStateAsserted) :
        dictUncoreExpBits['pxpd05f2_viral']['iio_viral_state']      = 1
        dictQpiExpBits   ['qpiviral']      ['qpi_viral_state']      = 1
        dictQpiExpBits   ['qpiviral']      ['qpi_pkt_viral_set']    = 1
    else :
        dictUncoreExpBits['pxpd05f2_viral']['iio_viral_state']      = 0
        dictQpiExpBits   ['qpiviral']      ['qpi_viral_state']      = 0
        dictQpiExpBits   ['qpiviral']      ['qpi_pkt_viral_set']    = 0



    if (bStatusAsserted) :
        dictUncoreExpBits['pxpd05f2_viral']['iio_viral_status']     = 1
        dictQpiExpBits   ['qpiviral']      ['qpi_viral_status']     = 1
    else :
        dictUncoreExpBits['pxpd05f2_viral']['iio_viral_status']     = 0
        dictQpiExpBits   ['qpiviral']      ['qpi_viral_status']     = 0




    return(dictUncoreExpBits, dictQpiExpBits)


#+----------------------------------------------------------------------------+
#|  Check all register bits necessary to confirm that Viral is enabled
#|  properly
#|
#|  Inputs:     Script command line options
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkViral(oCmdlineOptions):
    nErrors = 0
    sktList = _sockets.getAll()

    # Define data structures to keep track of all the registers/fields
    # we need to check.  The expected values in this structure come
    # from the command line arguments specified by the user
    (dictUncoreExpBits, dictQpiExpBits) = defineExpRegVals(
                                                            oCmdlineOptions.ViralEnabled,
                                                            oCmdlineOptions.ViralState,
                                                            oCmdlineOptions.ViralStatus,
                                          )
    _log.info("I'm checking the following conditions in your system:")
    _log.info("    Viral Enabled:         %s" % str(oCmdlineOptions.ViralEnabled))
    _log.info("    Viral State  Asserted: %s" % str(oCmdlineOptions.ViralState))
    _log.info("    Viral Status Asserted: %s" % str(oCmdlineOptions.ViralStatus))

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
    _log.result("I found %d errors while checking registers related to Viral." % nErrors)
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
    bErrorsOccurred = not checkViral(oCmdlineOptions)

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


