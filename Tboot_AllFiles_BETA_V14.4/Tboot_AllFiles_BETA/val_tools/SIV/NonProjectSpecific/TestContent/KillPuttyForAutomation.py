#!/usr/bin/env python
#+----------------------------------------------------------------------------+
#| INTEL CONFIDENTIAL
#| Copyright 2014-2015 Intel Corporation All Rights Reserved.
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
#|
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  Fix direct call of subprocess for starting PuTTY to use library call
#+----------------------------------------------------------------------------+

"""
    INTEL CONFIDENTIAL - DO NOT RE-DISTRUBUTE
    Copyright Intel Corporation All Rights Reserved

    Author(s): Kiran Tumkur, Erik Gross
    Change Notification List: erik.gross@intel.com
    
    Purpose:   Starts new instance of PuTTY logging tool after killing any 
               existing instances of it 
"""

#+----------------------------------------------------------------------------+
#| SVN Keywords. If copy-pasting this to a new script, be sure and run 
#|  'svn propset svn:keywords "LastChangedDate LastChangedRevision HeadURL Id Header Author" <scriptname.py>' 
#|  before committing to SVN.
#|  Alternately, you can enable these keywords via Tortoise SVN via
#|      TortoiseSVN->Properties->New->Keywords and check all the boxes.
#+----------------------------------------------------------------------------+
#|
#| $Date: 2015-09-24 15:12:42 -0700 (Thu, 24 Sep 2015) $
#| $Revision: 198 $
#| $HeadURL: http://dpvsvn.dp.intel.com/svn/val_tools/Generic/NonProjectSpecific/Utilities/_PythonScriptTemplate.py $
#| $Id: PuttyRestartForAutomation.py 198 2015-09-24 22:12:42Z amr\egross $
#| $Header: https://jf4gapp1008.amr.corp.intel.com/svn/val_tools/Generic/NonProjectSpecific/SystemInformation/PuttyRestartForAutomation.py 198 2015-09-24 22:12:42Z amr\egross $
#| $Author: amr\egross $

__svn_lastchangeddate__ = "$LastChangedDate: 2015-09-24 15:12:42 -0700 (Thu, 24 Sep 2015) $"[18:-2]
__svn_lastchangedrev__  = long("$LastChangedRevision: 198 $"[22:-2])
__svn_headurl__         = "$HeadURL: http://dpvsvn.dp.intel.com/svn/val_tools/Generic/NonProjectSpecific/Utilities/_PythonScriptTemplate.py $"[10:-2]
__svn_id__              = "$Id: PuttyRestartForAutomation.py 198 2015-09-24 22:12:42Z amr\egross $"[5:-2]
__svn_header__          = "$Header: https://jf4gapp1008.amr.corp.intel.com/svn/val_tools/Generic/NonProjectSpecific/SystemInformation/PuttyRestartForAutomation.py 198 2015-09-24 22:12:42Z amr\egross $"[9:-2]
__svn_author__          = "$Author: amr\egross $"[9:-2]

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
from optparse import OptionParser
import time         as _time
import subprocess   as _subprocess

# pythonsv imports
#import common.toolbox as _toolbox

# Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

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


def parseCommandLine():
    """
    #+------------------------------------------------------------------------+
    #|  Handle Command Line Options
    #|
    #|  This functon defines all supported command line options and invokes the
    #|  methods used to extract those options from the user-supplied command line
    #|
    #|  Inputs:     None
    #|  Returns:    Command Line Options Object from OptionParser
    #|
    #+------------------------------------------------------------------------+
    """

    #  Create a parser object and add options to it
    parser = OptionParser()

    # Debug option to control debug output - don't delete me!
    parser.add_option("--debug", action="store_true",
                      dest="Debug", default=False,
                      help="Turn on DEBUG functionality of script.  This enables extra output and causes it not to actually kill PuTTY.")

    parser.add_option("--profile_name", action="store",
                      dest="ProfileString", default="SUT",
                      help="Indicates the PuTTY profile name to load for logging.  Default is 'SUT'")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug            option read as %s" % oCmdlineOptions.Debug           )
    lLogger.debug("ProfileString    option read as %s" % oCmdlineOptions.ProfileString   )

    #  Return options data structure
    return oCmdlineOptions


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
    """
    This function is the main body of the script.  It should contain the high-
    level flow of the script, calling functions as necessary.

    """
    #  Variable definitions
    bErrorsOccurred = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __svn_lastchangedrev__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Kill all existing instances of PuTTY
    sDescription    = "kill all instances of PuTTY."
    sCommand        = "taskkill /f /im putty.exe"
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=False, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess):
        bErrorsOccurred = True

    #  Wait for all processes to die
    lLogger.info("Waiting 5 sec for processes to die...")
    _time.sleep(0)

    #----
    # For some reason the above block doesn't seem to like the
    #  "start" command.  Haven't found a good solution, so using
    #  the code below instead
    #----

    #  Return boolean indicating whether we were successful or not
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,
                                            sScriptName, __svn_lastchangedrev__)
    return (not bErrorsOccurred)
    

####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


