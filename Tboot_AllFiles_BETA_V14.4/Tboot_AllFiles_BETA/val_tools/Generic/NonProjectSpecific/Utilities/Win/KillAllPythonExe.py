
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
#|   *  
#+----------------------------------------------------------------------------+
#|
#| $Date: 2016-09-28 15:21:52 -0700 (Wed, 28 Sep 2016) $
#| $Revision: 912 $
#| $HeadURL: https://dpvsvn2.amr.corp.intel.com/svn/nvmtools/Linux/DP/usr/local/NvmTools/bin/dimmPartitionMagic.py $
#| $Id: dimmPartitionMagic.py 912 2016-09-28 22:21:52Z ddalton $
#| $Header: https://dpvsvn2.amr.corp.intel.com/svn/nvmtools/Linux/DP/usr/local/NvmTools/bin/dimmPartitionMagic.py 912 2016-09-28 22:21:52Z ddalton $
#| $Author: ddalton $

__svn_lastchangeddate__ = "$LastChangedDate: 2016-09-28 15:21:52 -0700 (Wed, 28 Sep 2016) $"[18:-2]
__svn_lastchangedrev__  = long("$LastChangedRevision: 912 $"[22:-2])
__svn_headurl__         = "$HeadURL: https://dpvsvn2.amr.corp.intel.com/svn/nvmtools/Linux/DP/usr/local/NvmTools/bin/dimmPartitionMagic.py $"[10:-2]
__svn_id__              = "$Id: dimmPartitionMagic.py 912 2016-09-28 22:21:52Z ddalton $"[5:-2]
__svn_header__          = "$Header: https://dpvsvn2.amr.corp.intel.com/svn/nvmtools/Linux/DP/usr/local/NvmTools/bin/dimmPartitionMagic.py 912 2016-09-28 22:21:52Z ddalton $"[9:-2]
__svn_author__          = "$Author: ddalton $"[9:-2]

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
from optparse import OptionParser
import time as _time
import cStringIO as _cStringIO


# PythonSV imports
import common.toolbox as _toolbox

# Global Variables/Constants
bDebug                  = True
nOutputWidth            = 80
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())


# val_tools DAL Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + (_os.sep+"..")*3 + _os.sep+"val_tools"   #  <--- make sure this is the correct relative path!
if (bDebug): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDebug):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)

#  Since we may want to import functionality from this script into another script,
#  only create the Logger instance if this is executing as a script and not being
#  imported as a module
if __name__ == '__main__':
    _log = _toolbox.getLogger()
    

def setupLogger(bDebug, sLogFileName):
    """
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
    """
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

def printStartupBanner(nOutputWidth, sScriptName, sVersion):
    """
    #+----------------------------------------------------------------------------+
    #|  Function To Print Generic Startup Banner
    #|
    #|  Inputs:     None
    #|  Returns:    1 on success; otherwise, 0
    #|
    #+----------------------------------------------------------------------------+"""
    sStartTime = _time.asctime(_time.localtime())
    LogDelimiter(nOutputWidth)
    _log.info(" %s(v%s) started on %s" % (sScriptName, sVersion, sStartTime))
    LogDelimiter(nOutputWidth)
    return 1

def LogDelimiter(nOutputWidth):
    """
    #+----------------------------------------------------------------------------+
    #|  Function To Print A Standard-width Delimiter to the Screen/Logfile
    #|
    #|  Inputs:     
    #|              nOutputWidth:    intended width of delimiter, in characters
    #|
    #|  Returns:    1 on success; otherwise, 0
    #|
    #+----------------------------------------------------------------------------+"""
    _log.info("=" * nOutputWidth)
    return 1

def printFinishingBanner(bErrorsOccurred, nOutputWidth, sScriptName, sVersion):
    """
    #+----------------------------------------------------------------------------+
    #|  Function To Print Generic Finishing Banner
    #|
    #|  Inputs:     
    #|              bErrorsOccurred:    indicates whether script was successful
    #|
    #|  Returns:    1 on success; otherwise, 0
    #|
    #+----------------------------------------------------------------------------+"""
    sStatus = "unsuccessfully" if bErrorsOccurred else "successfully"
    sEndTime = _time.asctime(_time.localtime())   
    LogDelimiter(nOutputWidth)
    _log.info(" %s(v%s) finished %s on %s" % (sScriptName, sVersion,
                                              sStatus, sEndTime))
    LogDelimiter(nOutputWidth)
    return 1

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
                      help="Turn on DEBUG functionality of script.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        _log.setFileLevel(_toolbox.DEBUG)
        _log.setConsoleLevel(_toolbox.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    _log.debug("Debug            option read as %s" % oCmdlineOptions.Debug           )

    #  Return options data structure
    return oCmdlineOptions

def parseLogFile():
    """
    Quick, stupid search for, and kill of all Python.Exe processes except this one... (which should terminate at the end of this script)
    """
    errorsDetected = 0
    _log.result("Looking for all Python.exe processes")
    # Get the Windows Tasklist
    tasklist = _os.popen('tasklist').readlines()
    _log.debug("Debumping Tasklist")
    for line in tasklist:
        _log.debug("\t%s" % line.strip())
    _log.debug("END TASKLIST")
    
    processes = []
    # Look for Python.exe processes and print them
    _log.debug("Searching for Python.exe Processes...")
    for line in tasklist:
        if line.count("python") and not line.count("%s" % _os.getpid()):
            _log.debug("\t%s" % line)
            processes.append(line)
            
    
    # Eliminate the ones that aren't this one
    _log.debug("Killing python processes that aren't this running process")
    for proc in processes:
        # Capture STD out from tskill
        stdout_backup = _sys.stdout
        stream = _cStringIO.StringIO()
        _sys.stdout = stream
        #'pythonw.exe 7892' 
        sProcess = proc.split("Console")[0]
        pid = int(sProcess.split("python.exe")[-1].strip()) if not sProcess.count("pythonw.exe") else int(sProcess.split("pythonw.exe")[-1].strip())
        _log.debug("Running: 'tskill %s'" % pid)
        alive = _os.system('tskill %s' % pid)
        _sys.stdout = stdout_backup
        output = stream.getvalue()
        if alive:
            _log.error("Unable to kill process: %s" % output)
            errorsDetected = 1
               
    if not errorsDetected: _log.result("No error's found.")
    else:
        # If it doesn't, error out!!!
        _log.error("ERROR: uefi/NvmCliPhase1.log Does not exist.  DIMM Partitioning likely did not happen.")
        errorsDetected = 1
    return errorsDetected

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

    If this is only a library (not to be run standalone), add the following
    code instead of what's below:

    --- Begin Library Code ---
    filename_wo_py = _os.path.basename(__file__).replace('.py', '')
    print("This script has nothing implemented in its main. Start python and use "
          "'import %s; dir(%s) to explore.'" % (filename_wo_py, filename_wo_py))
    --- End Library Code ---

    """
    #  Variable definitions
    bErrorsOccurred = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    setupLogger(bDebug, sLogfileName)
    printStartupBanner(nOutputWidth, sScriptName, __svn_lastchangedrev__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

    #  Meat of script
    bErrorsOccurred = parseLogFile()

    #  Return boolean indicating whether we were successful or not
    printFinishingBanner(bErrorsOccurred, nOutputWidth, sScriptName, __svn_lastchangedrev__)
    return (not bErrorsOccurred)
    

####################################################################################

if __name__ == '__main__':
    if main():
        _log.result("Exiting with zero status...")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        _log.error("Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully


