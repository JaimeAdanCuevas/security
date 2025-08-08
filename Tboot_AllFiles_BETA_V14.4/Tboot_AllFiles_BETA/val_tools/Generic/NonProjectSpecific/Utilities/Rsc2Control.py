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
#| $Id: Rsc2Control.py 151 2015-03-23 21:50:48Z amr\egross $
#| $Date: 2015-03-23 14:50:48 -0700 (Mon, 23 Mar 2015) $
#| $Author: amr\egross $
#| $Revision: 151 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  Add comments and function descriptins - this is just an initial cut!!!
#+----------------------------------------------------------------------------+

"""
    Write something here that summarizes what this script does
"""

# Standard libary imports
import os       as _os
import sys      as _sys
import re       as _re
import logging  as _logging
import time     as _time
from optparse import OptionParser

# Import the RSC2 library, and make sure that we know its standard path if it's
# not already in sys.path
if 'C:\\Program Files (x86)\\RSC 2 Software\\Python Extension Library\\x64\\Python26' not in _sys.path:
    _sys.path.insert(0,'C:\\Program Files (x86)\\RSC 2 Software\\Python Extension Library\\x64\\Python26')
import rsc2     as _rsc2



## Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 151 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
AC_OFF_DEFAULT_WAIT     = 5    # in Seconds
POLL_TIME_POWER         = 5    # in Seconds
MAX_WAIT_OFF            = 60  # number of polling intervals
MAX_WAIT_ON             = 60  # number of polling intervals

# val_tools Utilities Import - gotta find it first!
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

    parser.add_option("--cycleac", action="store_true", dest="CycleAc", 
                      default="False",
                      help="Use the RSC2 to cycle the AC Power.  Assume system is on, and we need to turn it off and back on again.")

    parser.add_option("--platform_type", action="store", dest="PlatformType", 
                      type="choice", choices=["ThunderRidge"], default=None,
                      help="[optional] Type of being used.  e.g. 'ThunderRidge' or 'MayanCity'")

    parser.add_option("--platform_initial_state", action="store", dest="PlatformInitialState", 
                      type="choice", choices=["G0", "G2", "G3"], default="G0",
                      help="Indicates ACPI state the system should be in at the start of this script.")

    parser.add_option("--platform_initial_state_timeout", action="store", dest="PlatformInitialStateTimeout", 
                      type="int", default=60,
                      help="Time (in multiples of %s seconds) for the script to wait for the system to achieve the expected initial platform state before starting AC cycle or giving up." % POLL_TIME_POWER)

    parser.add_option("--delay", action="store", dest="ResetDelay", type=int,
                      default=0,
                      help="Indicates an optional delay (in seconds) to introduce\
                            before resetting the system.")


    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug                       Option read as %s"  % oCmdlineOptions.Debug                       )
    lLogger.debug("CycleAc                     Option read as %s"  % oCmdlineOptions.CycleAc                     )
    lLogger.debug("PlatformType                Option read as %s"  % oCmdlineOptions.PlatformType                )
    lLogger.debug("PlatformInitialState        Option read as %s"  % oCmdlineOptions.PlatformInitialState        )
    lLogger.debug("PlatformInitialStateTimeout Option read as %s"  % oCmdlineOptions.PlatformInitialStateTimeout )
    lLogger.debug("ResetDelay                  Option read as %s"  % oCmdlineOptions.ResetDelay                  )

    #  Return options data structure
    return oCmdlineOptions


#+----------------------------------------------------------------------------+
#|  Wait for the specified amount of time
#|
#|  Inputs:     integer number of seconds to wait
#|  Returns:    1 on success; 0 otherwise
#|
#+----------------------------------------------------------------------------+
def waitForDelay(nDelay):
    lLogger.info("Delay of %4d seconds requested.  Waiting..." % nDelay)
    _time.sleep(nDelay)
    lLogger.info("    Done with delay... proceeding with script.")
    return 1


#+----------------------------------------------------------------------------+
#|  Print out the status of the 3 main LEDs for the RSC2
#|
#|  Inputs:     LED objects for the RSC2
#|  Returns:    True always
#|
#+----------------------------------------------------------------------------+
def printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber):
    lLogger.info("Power LED status is: %s" % str(ledStatusPower.getSigAssertionState()))
    lLogger.info("Green LED status is: %s" % str(ledStatusGreen.getSigAssertionState()))
    lLogger.info("Amber LED status is: %s" % str(ledStatusAmber.getSigAssertionState()))
    return True

#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkPlatform(sPlatform):
    if (sPlatform == None):
        lLogger.info("No specific platform specified.")
        lLogger.info("   Will only use default interpretations for platform LEDs.")
    elif (sPlatform == 'ThunderRidge'):
        lLogger.info("%s platform specified." % sPlatform)
    else:
        lLogger.error("Unknown platform specified: %s" % sPlatform)
        lLogger.error("    I don't know how to interpret the platform LEDs!")
        return False

    # If we get here, we're successful!
    return True


#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    RSC2 "Box" object
#|
#+----------------------------------------------------------------------------+
def getRsc2Box():
    box = None
    # Access the RSC2 on the local system, check that there's a box connected
    host = _rsc2.Host('localhost')
    if host.getNumBoxes() == 0:
        lLogger.error('No RSC2 devices connected to host.')
        return None
    
    # Try to get the first RSC2 box in the list
    try:
        box = host.getBox(0)
    except Exception, eGetBox:
        lLogger.error('There do not seem to be any RSC2 boxes connected to the local host')
        lLogger.error('    This would be a problem...')

    # Return whatever we got
    return box


#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkExpectedInitialPowerState(sPlatform, oCmdlineOptions, ledStatusPower):

    statePowerExpected = None
    # Each platform may have a different way of interpreting the Power LED on
    # the RSC2.  Have a separate if/elif block for each known platform
    if (sPlatform == "ThunderRidge" or sPlatform == None):
        # Determine Expected Initial Power State (based on command line option)
        if   (oCmdlineOptions.PlatformInitialState == "G0"):
            statePowerExpected = _rsc2.LED_ON
            lLogger.info("Expected platform initial state of ACPI %s means Power LED should be ON." % oCmdlineOptions.PlatformInitialState)
        elif (oCmdlineOptions.PlatformInitialState == "G2"):
            statePowerExpected = _rsc2.LED_OFF
            lLogger.info("Expected platform initial state of ACPI %s means Power LED should be OFF." % oCmdlineOptions.PlatformInitialState)
        elif (oCmdlineOptions.PlatformInitialState == "G3"):
            statePowerExpected = _rsc2.LED_OFF
            lLogger.info("Expected platform initial state of ACPI %s means Power LED should be OFF." % oCmdlineOptions.PlatformInitialState)
        else:
            lLogger.error("Unknown expected initial platform state from --platform_initial_state")
            return False
    else:
        lLogger.error("Unknown platform type specified: %s " % sPlatform)
        return False

    # Poll the system for the expected initial power status
    nCurrentWait = 0
    nMaxWaitIntervals = oCmdlineOptions.PlatformInitialStateTimeout
    while (
            (ledStatusPower.getSigAssertionState() != statePowerExpected) and 
            (nCurrentWait < nMaxWaitIntervals)
    ):
        lLogger.info("Power LED is not in expected state.  Waiting %s second(s)..." % POLL_TIME_POWER)
        lLogger.warn("    Current  Power LED status is: %s" % str(ledStatusPower.getSigAssertionState()))
        lLogger.warn("    Expected Power LED status is: %s" % str(statePowerExpected))
        _time.sleep(POLL_TIME_POWER)
        nCurrentWait = nCurrentWait + 1

    # Confirm Initial Power State (based on command line option)
    if (ledStatusPower.getSigAssertionState() == statePowerExpected):
        lLogger.info("Power LED  now indicates expected initial state")
    else:
        lLogger.error("Power LED is still not in expected state. ")
        lLogger.error("    Current  Power LED status is: %s" % str(ledStatusPower.getSigAssertionState()))
        lLogger.error("    Expected Power LED status is: %s" % str(statePowerExpected))
        return False
    return True


#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def killAcPower(ac1Button, ac2Button):
    # Turn off AC Power Switches
    lLogger.info("Turning off AC power")
    ac1Button.setSigAssertionState(_rsc2.BUTTON_RELEASED)
    ac2Button.setSigAssertionState(_rsc2.BUTTON_RELEASED)
    lLogger.info("Power should be off")

    # Wait for system to settle
    lLogger.info("Waiting a %s seconds for power to be fully off and for capacitors to discharge" % AC_OFF_DEFAULT_WAIT)
    _time.sleep(AC_OFF_DEFAULT_WAIT)
    return True


#+----------------------------------------------------------------------------+
#|  Enhance me for other platforms!
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def confirmAcPowerOff(sPlatform, ledStatusPower, ledStatusGreen, ledStatusAmber):

    nCurrentWait = 0
    expectedLedStatusPower = None
    expectedledStatusGreen = None
    expectedledStatusAmber = None
    printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)

    # Each platform may have a different way of interpreting the LEDs on
    # the RSC2.  Have a separate if/elif block for each known platform
    if (sPlatform == "ThunderRidge" or sPlatform == None):
        expectedLedStatusPower = _rsc2.LED_ON
        expectedledStatusGreen = _rsc2.LED_OFF
        expectedledStatusAmber = _rsc2.LED_OFF
    else:
        lLogger.error("Unknown platform type specified: %s " % sPlatform)
        return False

    # Poll the LED statuses until we get what we want or we time out
    while (
            (
                (ledStatusPower.getSigAssertionState() == expectedLedStatusPower) or
                (ledStatusGreen.getSigAssertionState() == expectedledStatusGreen) or
                (ledStatusAmber.getSigAssertionState() == expectedledStatusAmber)
            ) and 
            (nCurrentWait < MAX_WAIT_OFF)
        ):
        lLogger.warn("System not fully powered down! Waiting %s second(s)..." % POLL_TIME_POWER)
        printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)
        _time.sleep(POLL_TIME_POWER)
        nCurrentWait = nCurrentWait + 1

    # If system is still on, then we're done
    if (
                (ledStatusPower.getSigAssertionState() == expectedLedStatusPower) or
                (ledStatusGreen.getSigAssertionState() == expectedledStatusGreen) or
                (ledStatusAmber.getSigAssertionState() == expectedledStatusAmber)
    ):
        lLogger.error("System LEDs do not indicate a successful power down.")
        lLogger.error("    Not attempting to continue with AC cycle.")
        printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)
        lLogger.info("Expected Power LED status was: %s" % str(expectedLedStatusPower))
        lLogger.info("Expected Green LED status was: %s" % str(expectedledStatusGreen))
        lLogger.info("Expected Amber LED status was: %s" % str(expectedledStatusAmber))
        return False

    # Indicate the current status of the Power, Green, and Amber LEDs
    printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)

    # If we get here, we're successful!
    return True


#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def applyAcPowerAndConfirmPowerOn(sPlatform, ac1Button, ac2Button, ledStatusPower):

    expectedLedStatusPower = None

    # Each platform may have a different way of interpreting the LEDs on
    # the RSC2.  Have a separate if/elif block for each known platform
    if (sPlatform == "ThunderRidge" or sPlatform == None):
        expectedLedStatusPower = _rsc2.LED_ON
    else:
        lLogger.error("Unknown platform type specified: %s " % sPlatform)
        return False

    # Turn the power back on
    lLogger.info("Turning AC Power back on...")
    ac1Button.setSigAssertionState(_rsc2.BUTTON_PRESSED)
    ac2Button.setSigAssertionState(_rsc2.BUTTON_PRESSED)

    # Wait until the system's power LED comes on or we time out
    nCurrentWait = 0
    while (ledStatusPower.getSigAssertionState() == _rsc2.LED_OFF) and (nCurrentWait < MAX_WAIT_ON):
        lLogger.warn("    Power LED is still off! Waiting %s second(s)..." % POLL_TIME_POWER)
        _time.sleep(POLL_TIME_POWER)
        nCurrentWait = nCurrentWait + 1

    # If system is still off, then we're done
    if (ledStatusPower.getSigAssertionState() == expectedLedStatusPower):
        lLogger.info("Power LED indicates a successful power on.")
    else:
        lLogger.error("Power LED does not indicate a successful power on.")
        lLogger.error("    Something appears to have gone wrong when reapplying power.")
        printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)
        return False

    # If we get here, we're successful!
    return True


#+----------------------------------------------------------------------------+
#|  
#|
#|  Inputs:     
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def foo(sPlatform):
    return True


#+----------------------------------------------------------------------------+
#|  Function Do Something Useful
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def cycleAc(oCmdlineOptions):

    # Check for known platform
    sPlatform = oCmdlineOptions.PlatformType
    if not checkPlatform(sPlatform):
        return False

    # Create a "Box" object to interact with the RSC2
    box = getRsc2Box()
    if (box == None):
        lLogger.error("Unable to find an RSC2 box connected to the local system")
        return False
    
    # Get references to some RSC2 signals we'll need later
    buttonPower     = box.getSignal(_rsc2.ID_FPBUT_PWR)
    jumperMfgMode   = box.getSignal(_rsc2.ID_JMP_MFG_MODE)
    ledStatusGreen  = box.getSignal(_rsc2.ID_LED_STATUS_GREEN)
    ledStatusAmber  = box.getSignal(_rsc2.ID_LED_STATUS_AMBER)
    ledStatusPower  = box.getSignal(_rsc2.ID_LED_PWR)
    ac1Button       = box.getSignal(_rsc2.ID_AC_1)
    ac2Button       = box.getSignal(_rsc2.ID_AC_2)

    # Confirm AC Power is ON
    lLogger.info("AC Switch1 status is: %s" % str(ac1Button.getSigAssertionState()))
    lLogger.info("AC Switch2 status is: %s" % str(ac2Button.getSigAssertionState()))
    if (
        (ac1Button.getSigAssertionState() == _rsc2.BUTTON_RELEASED) or
        (ac1Button.getSigAssertionState() == _rsc2.BUTTON_RELEASED)
    ):
        lLogger.error("AC power is already off.  Wasn't expecting it to be off already!")
        return False

    # Indicate the current status of the Power, Green, and Amber LEDs
    printLedStatus(ledStatusPower, ledStatusGreen, ledStatusAmber)

    # Verify Initial Power State (based on command line option)
    if not checkExpectedInitialPowerState(sPlatform, oCmdlineOptions, ledStatusPower):
        lLogger.error("Platform is not in the initial state expected.  Aborting...")
        return False

    # Kill AC Power
    if not killAcPower(ac1Button, ac2Button):
        lLogger.error("Removal of AC port failed.  Aborting...")
        return False

    # Check/poll the system to ensure it actually turned off
    if not confirmAcPowerOff(sPlatform, ledStatusPower, ledStatusGreen, ledStatusAmber):
        lLogger.error("System still not powerd down.  Aborting...")
        return False


    # Reapply AC power and confirm that system is powered on(G0, not G2)
    # NOTE: this assumes validation platforms are set to power on immediately
    #       after the application of AC power.  If this is not the case, then
    #       another command line option should be added to simulate pushing
    #       the power button after reapplying AC power.
    if not applyAcPowerAndConfirmPowerOn(sPlatform, ac1Button, ac2Button, ledStatusPower):
        lLogger.error("System has not powered on after reapplying AC power.")
        lLogger.error("   This is definitely not good.  Check your BIOS settings for power.")
        lLogger.error("   fail behavior == PowerOn.")
        return False

    # If we get here, we're successful!
    return True


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
    oCmdlineOptions = parseCommandLine()

    #  If user requested a delay before reset, do that
    if (oCmdlineOptions.ResetDelay > 0):
        bErrorsOccurred = not waitForDelay(oCmdlineOptions.ResetDelay)

    #  Do the action requested by the user
    if (oCmdlineOptions.CycleAc == True):
        bErrorsOccurred = not cycleAc(oCmdlineOptions)


    #  Return boolean indicating whether we were successful or not
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,
                                            sScriptName, __version__)
    return (not bErrorsOccurred)
    

####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


