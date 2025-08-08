#!/usr/bin/env python
# +----------------------------------------------------------------------------+
# | INTEL CONFIDENTIAL
# | Copyright 2014-2015 Intel Corporation All Rights Reserved.
# |
# | The source code contained or described herein and all documents related
# | to the source code ("Material") are owned by Intel Corporation or its
# | suppliers or licensors. Title to the Material remains with Intel Corp-
# | oration or its suppliers and licensors. The Material may contain trade
# | secrets and proprietary and confidential information of Intel Corpor-
# | ation and its suppliers and licensors, and is protected by worldwide
# | copyright and trade secret laws and treaty provisions. No part of the
# | Material may be used, copied, reproduced, modified, published, uploaded,
# | posted, transmitted, distributed, or disclosed in any way without
# | Intel's prior express written permission.
# |
# | No license under any patent, copyright, trade secret or other intellect-
# | ual property right is granted to or conferred upon you by disclosure or
# | delivery of the Materials, either expressly, by implication, inducement,
# | estoppel or otherwise. Any license under such intellectual property
# | rights must be express and approved by Intel in writing.
# |
# +----------------------------------------------------------------------------+

#
#     INTEL CONFIDENTIAL - DO NOT RE-DISTRUBUTE
#     Copyright Intel Corporation All Rights Reserved
#
#     Author(s): vanila.reddy@intel.com
#
#     Script that parses the serial and return the user with useful information about the Security Techonlogies Enabled and TPM type information.
#     Right now Parser Implemented for TXT and BtG ( CBnT)
#

# +----------------------------------------------------------------------------+

# Standard libary imports
import os as _os
import re as _re
from collections import namedtuple
import logging as _logging
from optparse import OptionParser
import sys as _sys
import subprocess as _subprocess
import glob

# Global Variables/Constants
bDebug = False
nOutputWidth = 80
__version__ = "$Rev: 172 $".replace("$Rev:","").replace("$","").strip()
sScriptName = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName = '%s_pid%d.log' % (sScriptName, _os.getpid())
Success = 1
Fail = 0
# Set up logging to file
"""logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',filemode='w')
_logger=logging.getLogger(__name__)"""
sScriptPath = _os.path.dirname(__file__)

#print sScriptPath
if (bDebug):
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../Generic/NonProjectSpecific/Utilities"  # <--- make sure this is the correct relative path!
#print sUtilitiesPath
if (bDebug):
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath = _os.path.normpath(sUtilitiesPath)
#print sUtilitiesPath
if (bDebug):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

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
                      help="Turn on DEBUG functionality of script.")

    parser.add_option("--user_input", action="store", dest="UserInput",
                      type="choice", choices=["SystemInfo", "BtGProfile", "TPMInfo","TxtInfo","BtGInfo","BtGProfile3","BtGProfile4","BtGProfile5","BtGProfile0"], default="SystemInfo",
                      help="Please Input the option for information, Avaliable Options are : 'SystemInfo','BtGProfile','TPMInfo','TxtInfo','BtGInfo','BtGProfile3','BtGProfile4',''BtGProfile5','BtGProfile0' !")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug

    # Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug            option read as %s" % oCmdlineOptions.Debug)
    lLogger.debug("UserInput  option read as %s" % oCmdlineOptions.UserInput)

    #  Return options data structure
    return oCmdlineOptions


#
# +------------------------------------------------------------------------+
# |  Function that analysis BootGuard Profile
# |
# |  Inputs:     None
# |  Returns:    True on success; otherwise, False
# |
# +------------------------------------------------------------------------+
#

def BootGuard_Profile_Analysis(bootguardvalues,Profile_Type_Check,Type):
    # Defining Named Tuple
    boot_guard_profile = namedtuple('BtGProfile',
                                    'BootGuardProfile LtStatusRegister LtExtendedStatusError BootGuardBootStatus BootGuardAcmError MSR_BOOT_GUARD_SACM_INFO')

    # BootGuard Profiles with different config:
    btgP0_TXT = boot_guard_profile('BootGuard Profile 0 and TXT is Enabled', '0x0000000000004092', '0x0000000000000000',
                                   '0xD554000000000000', '0x00000C81C0008003', '0x0000000400000000')
    btgP3_1_2 = boot_guard_profile('BootGuard Profile 3 with TXT Enabled and TPM 1.2', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x000000070000006B')
    btgP3_2_0 = boot_guard_profile('BootGuard Profile 3 with TXT Enabled and TPM 2.0', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x000000070000006D')
    btgP4_1_2 = boot_guard_profile('BootGuard Profile 4 with TXT Enabled and TPM 1.2', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x0000000700000051')
    btgP4_2_0 = boot_guard_profile('BootGuard Profile 4 with TXT Enabled and TPM 2.0', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x0000000700000051')
    btgP5_1_2 = boot_guard_profile('BootGuard Profile 5 with TXT Enabled and TPM 1.2', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x000000070000007B')
    btgP5_2_0 = boot_guard_profile('BootGuard Profile 5 with TXT Enabled and TPM 2.0', '0x0000000000004092',
                                   '0x0000000000000000', '0xD554000000000000', '0x00000C81C0008003',
                                   '0x000000070000007D')
    btgP5_P4 = boot_guard_profile('BootGuard Profile 5 downgraded to Profile 4 and TPM has been disabled',
                                  '0x0000000000004092', '0x0000000000000000', '0xD554000000000000',
                                  '0x00000C81C0008003', '0x0000000700000051')

    # Mapping the BtG Profiles above into a list
    profile_analysis = [btgP0_TXT, btgP3_1_2, btgP3_2_0, btgP4_1_2, btgP4_2_0, btgP5_1_2, btgP5_2_0, btgP5_P4]

    try:
        with open(bootguardvalues, "r") as output_file:
            for line in output_file:
                if line.startswith('MSR_BOOT_GUARD_SACM_INFO ='):
                    num = line.split('=')[-1].strip()
                    for sublist in profile_analysis:
                        if Profile_Type_Check == False:
                            if sublist[5] == num:
                                lLogger.info(sublist.BootGuardProfile)
                                #lLogger.info(sublist.MSR_BOOT_GUARD_SACM_INFO)
                    if Profile_Type_Check:
                        lLogger.info(Type)
                        if (Type == 3) and (num == '0x000000070000006B' or num == '0x000000070000006D'):
                            lLogger.info("BtGP3 is enabled")
                            return Success
                        elif (Type == 4) and (num == '0x0000000700000051'):
                            lLogger.info("BtGP4 is enabled")
                            return Success
                        elif (Type == 5) and (num == '0x000000070000007B' or num == '0x000000070000007D'):
                            lLogger.info("BtGP5 is enabled")
                            return Success
                        elif (Type == 0) and (num == '0x0000000400000000'):
                            lLogger.info("BtGP0 is enabled")
                            return Success
                        else:
                            lLogger.info("Fail")
                            return Fail
    except:
        lLogger.info("Couldn't find the file , please check if the directory path or the filename has been changed.....!!!")
        return Fail
    return Success

    # +------------------------------------------------------------------------+
    # |  Function that return information on Type of TPM enabled.
    # |
    # |  Inputs:     None
    # |  Returns:    True on success; otherwise, False
    # |
    # +------------------------------------------------------------------------+


#
def parser(string_list, output_file, serial_file_to_parse):
    if not _os.path.isfile(serial_file_to_parse):
        lLogger.error("The file to parse doesn't exist..!!!")
        raise IOError("The file to parse doesn't exist..!!!")
    if not string_list:
        lLogger.error("The List is empty need to contain value to lookup in file")
        raise ValueError("The List is empty need to contain values to lookup in file")

    line_regex = _re.compile(r'..*''|'.join(string_list))

    output_filename = _os.path.normpath(output_file)

    with open(output_filename, "w") as out_file:
        out_file.write("")

    with open(output_filename, "a") as out_file:
        try:
            with open(serial_file_to_parse, "r") as in_file:
                lLogger.info("Looking the serial file for information........")
                seen = set()
                # Loop over each log line
                for line in in_file:
                    if (line_regex.search(line)) and line not in seen:
                        seen.add(line)
                        lLogger.info(line)
                        out_file.write(line)
                lLogger.info("%s succesfully generated.....", output_file)
        except:
            lLogger.error("Cant find the serial log for %s parsing...", output_file)
            return Fail
    return Success

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
    commandlineoptions = parseCommandLine()

    if (commandlineoptions.UserInput == "BtGProfile"):
        Profile_Type_Check=False
        Type=0
        lLogger.info(" ")
        lLogger.info("              The Current BootGuard Profile Enabled on System...              ")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError']
        filetoparse = "C:\Temp\BtGP3.log"
        filetologinfo = "C:\BootGuard_Values.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "BtGProfile3"):
        Profile_Type_Check=True
        Type=3
        lLogger.info(" ")
        lLogger.info("              The Current BootGuard Profile Enabled on System...              ")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError']
        filetoparse = "C:\Temp\BtGP3.log"
        filetologinfo = "C:\BootGuard_Values.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "BtGProfile4"):
        Profile_Type_Check=True
        Type=4
        lLogger.info(" ")
        lLogger.info("              The Current BootGuard Profile Enabled on System...              ")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError']
        filetoparse = "C:\Temp\BtGP4.log"
        filetologinfo = "C:\BootGuard_Values.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "BtGProfile5"):
        Profile_Type_Check=True
        Type=5
        lLogger.info(" ")
        lLogger.info("              The Current BootGuard Profile Enabled on System...              ")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError']
        filetoparse = "C:\Temp\BtGP5.log"
        filetologinfo = "C:\BootGuard_Values.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "BtGProfile0"):
        Profile_Type_Check=True
        Type=0
        lLogger.info(" ")
        lLogger.info("              The Current BootGuard Profile Enabled on System...              ")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError']
        filetoparse = "C:\Temp\BtGP0.log"
        filetologinfo = "C:\BootGuard_Values.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "TPMInfo"):
        lLogger.info(" ")
        lLogger.info("              The TPM information listed below...             ")
        lLogger.info(" ")
        string_search = ['PTT', 'TPM Device Present', 'TPM2.0: dTPM Enabled']
        filetoparse = "C:\Temp\putty.log"
        filetologinfo = "C:\TPM_Information.log"
        parser(string_search, filetologinfo, filetoparse)
    elif (commandlineoptions.UserInput == "SystemInfo"):
        Profile_Type_Check=False
        Type=0
        lLogger.info(" ")
        lLogger.info("The System information listed below...")
        lLogger.info(" ")
        string_search = ['LtStatusRegister', 'BootGuardBootStatus', 'MSR_BOOT_GUARD_SACM_INFO', 'LtExtendedStatusError',
                         'BootGuardAcmError', 'PTT', 'TPM Device Present', 'TPM2.0: dTPM Enabled']
        f1 = glob.glob("C:\Temp\putt*")
        filetoparse = f1[0]
        lLogger.info(filetoparse)
        filetologinfo = "C:\System_Information.log"
        parser(string_search, filetologinfo, filetoparse)
        BootGuard_Profile_Analysis(filetologinfo,Profile_Type_Check,Type)
    elif (commandlineoptions.UserInput == "TxtInfo"):
        lLogger.info(" ")
        lLogger.info("                The useful information from TxtInfo tool is listed .... ")
        lLogger.info(" ")
        string_search = ['STS: SExit Done','STS: SExit Done','TXT Errorcode','TXT ACM status','TXT ACM Errorcode','Type 10 record','TXT Enabled']
        _subprocess.call("dos2unix /run/media/root/LIVE/TxtInfo.log /run/media/root/LIVE/TxtInfo.log",shell=True)
        filetoparse="/run/media/root/LIVE/TxtInfo.log"
        lLogger.info(filetoparse)
        filetologinfo="/root/TxtInfo_Information.log"
        parser(string_search,filetologinfo,filetoparse)
    elif (commandlineoptions.UserInput == "BtGInfo"):
        lLogger.info(" ")
        lLogger.info("                  The useful information from BtGInfo tool is listed .... ")
        lLogger.info(" ")
        string_search = ['Btg ACM Status','TPM Success','Force Ancor Cove Boot','Measured Boot','Verified Boot','TXT Errorcode','Class Code','Major code','Minor code','Module type','TXT/BtG ACM status','ACMSTS','TXT ACM Errorcode']
        _subprocess.call("dos2unix /run/media/root/LIVE/BtGInfo.log /run/media/root/LIVE/BtGInfo.log",shell=True)
        filetoparse="/run/media/root/LIVE/BtGInfo.log"
        filetologinfo="/root/BtGInfo_Information.log"
        parser(string_search,filetologinfo,filetoparse)
    else:
        lLogger.error("Unknown user option '%s'" % commandlineoptions.UserInput)
        bErrorsOccurred = True

    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,
                                            sScriptName, __version__)
    return (not bErrorsOccurred)


if __name__ == '__main__':
    if main():
        lLogger.info("\n Exiting with zero status ")
        _sys.exit(0)  # zero exit status means script completed successfully
    else:
        lLogger.error("\n Exiting with non-zero status...")
        _sys.exit(1)  # non-zero exit status means script did not complete successfully
