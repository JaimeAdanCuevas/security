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
#| $Id: WaitForS5ThenPowerOn.py 177 2015-05-12 21:49:35Z amr\egross $
#| $Date: 2015-05-12 14:49:35 -0700 (Tue, 12 May 2015) $
#| $Author: amr\egross $
#| $Revision: 177 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Script to wait for Target power off and then pulse PWRGD signal to turn on
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import time         as _time
from optparse import OptionParser

# pythonsv imports
import common.toolbox as _toolbox
import itpii
import common.baseaccess as baseaccess 


# Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 177 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
_log                    = _toolbox.getLogger()
itp                     = itpii.baseaccess()

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
                      help="Run with debug output and don't acutally reset the system.")

    parser.add_option("--force_pwrgood", action="store_true", dest="ForcePowergood", 
                      default=False,
                      help="If the script reaches the timeout waiting for \
                            detection of S5/G2, then this option will cause it\
                            to pulse the Power Good signal anyway.  Default\
                            behavior is to assume something went wrong and NOT\
                            reset the system.")

    parser.add_option("--poll_interval", action="store", dest="PollInterval", 
                      type="int", default=10,
                      help="Interval in which to poll the system to see if it\
                            has turned off yet.  Setting to 10 will check\
                            once every 10 seconds.")

    parser.add_option("--max_intervals", action="store", dest="MaxIntervals", 
                      type="int", default=60,
                      help="Maximum number of polling intervals to check for\
                            system to power off.  If this maximum is exceeded,\
                            the script will either exit with an error status\
                            (default behavior) or pulse Power Good anyway and\
                            exit with zero status (if --force_pwrgood is set).")

    parser.add_option("--poweron_delay", action="store", dest="PowerOnDelay", 
                      type="int", default=0,
                      help="Interval in which to wait after pulsing PWRGOOD\
                            before executing further DAL commands.  This may help\
                            if you find the script behaving oddly at the very end.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug          Option read as %s" % oCmdlineOptions.Debug         )
    _log.debug("ForcePowergood Option read as %s" % oCmdlineOptions.ForcePowergood)
    _log.debug("PollInterval   Option read as %s" % oCmdlineOptions.PollInterval  )
    _log.debug("MaxIntervals   Option read as %s" % oCmdlineOptions.MaxIntervals  )
    _log.debug("PowerOnDelay   Option read as %s" % oCmdlineOptions.PowerOnDelay  )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
## Function to poll DAL's "targpower" control variable
##   to determine if the system has powered down yet
#|
#|  Inputs:     
#|              Interval (seconds) in which to poll for PowerDown
#|              Maximum intervals to poll before giving up
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def PollForPowerDown(nPollInterval, nMaxIntervals):

    #  Check for Target Power Off
    #    If not off, wait one interval and try again
    #    If maximum intervals waited, exit loop
    nWaitCount = 0
    while ((itp.cv.targpower == True) and (nWaitCount < nMaxIntervals)) :
        _log.info("System is still powered on.  Waiting %d sec..." % nPollInterval)
        _time.sleep(nPollInterval)
        nWaitCount = nWaitCount + 1
    
    #  If system is still on, flag error
    if (itp.cv.targpower == True):
        return False

    return True


#+----------------------------------------------------------------------------+
## Function to use DAL command to power on the system via PwrGood
#|
#|  Inputs:     
#|              Boolean indicating whether we're in debug mode or not
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def PulsePowerGoodSignal(bDebug):
    #  Check for --debug option; if set, then don't actually reset the system
    if (bDebug):
        _log.result("--debug option specified.  This is the point where I would")
        _log.result("    normally pulse the Power Good signal.  I'm not actually")
        _log.result("    gonna do it, though.")
    else:
        #  Try to pulse the Power Good signal, and inform user if error occurs
        try:
            itp.pulsepwrgood()
        except Exception, ePowerGood :
            _log.error("\n\001ired\001ERROR: ITP command to pulse the PWRGOOD signal (itp.pulsepwrgood) failed.")
            _log.error("       ITP error: %s" %ePowerGood)
            return False
        else:
            _log.result("\001igreen\001PwrGood signal successfully pulsed.\n\001igreen\001")
            
    #  If we made it this far, then return success
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
    bErrorsOccurred         = False # used to short-circuit certain steps if errors found
    #  Variables to indicate success of key parts of script
    bPowerDownSuccess       = False
    bPwrGoodSuccess         = False
    bPowerUpSuccess         = False


    #  Startup tasks - get the logger configured
    _ValToolsDalUtilities.setupLogger(bDebug, sLogfileName)
    _ValToolsDalUtilities.printStartupBanner(nOutputWidth, 
                                             sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Wait for system to turn off
    bPowerDownSuccess =  PollForPowerDown(oCmdlineOptions.PollInterval,
                                          oCmdlineOptions.MaxIntervals)

    #  If PowerDown was unsuccessful, then print error message
    if (not bPowerDownSuccess):
        if (oCmdlineOptions.ForcePowergood):
            _log.info("The system is still powered on.  That's bad news, but...")
            _log.info("    you specified --force_pwrgood, so I'm gonna pretend")
            _log.info("    the system actually powered down and proceed anyway")
            #  Fake that the system powered down successfully
            bPowerDownSuccess = True
        else:
            _log.error("\001ired\001Whoa!  The system is still powered on.  That's bad news...")
            _log.error("\001ired\001   NOT resetting system.")
    else:
        _log.result("\001igreen\001The system has powered off.")
        _log.result("   Now pulsing PWRGOOD signal to turn the system back on")

    #  Attempt to power up the system if it successfully shut down
    if (bPowerDownSuccess):
        bPwrGoodSuccess = PulsePowerGoodSignal(oCmdlineOptions.Debug)

        if (not bPwrGoodSuccess):
            _log.error("DAL command to pulse Power Good was unsuccessful.  System may")
            _log.error("    not be in a good state.")
            bPowerUpSuccess = False
        else:
            #  Wait for optional delay period to give the DAL a chance
            #  to reconfigure the debug port before we try to execute
            #  DAL commands or end the script (which shuts down the DAL interface)
            if (oCmdlineOptions.PowerOnDelay > 0):
                _log.info("PowerOnDelay of %d sec specified.  Waiting..." % oCmdlineOptions.PowerOnDelay)
                _time.sleep(oCmdlineOptions.PowerOnDelay)

            #  If DAL reports success for PulsePwrGood, verify that
            #      system has powered up (and presumably is POSTing)
            if (itp.cv.targpower == True):
                _log.result("\001igreen\001The system has powered on and should be booting now.")
                bPowerUpSuccess = True
      
            #  If system is still off, then something went wrong
            else:
                _log.error("\001ired\001The system is still powered down after pulsing the PWRGOOD signal.")
                _log.error("\001ired\001   Something went wrong.  Exiting with non-zero status.")
                bPowerUpSuccess = False

    #  We're done!
    _ValToolsDalUtilities.printFinishingBanner(bErrorsOccurred, nOutputWidth,
                                            sScriptName, __version__)
    return ((not bErrorsOccurred) and 
            bPowerDownSuccess and
            bPwrGoodSuccess and 
            bPowerUpSuccess)

####################################################################################

if __name__ == '__main__':
    if main():
        _log.result("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        _log.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


