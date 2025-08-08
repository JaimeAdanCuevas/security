#!/usr/bin/env python
#+----------------------------------------------------------------------------+
#|INTEL CONFIDENTIAL
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
#| $Id: CreateLaunchControlPolicy.py 172 2015-04-30 00:05:40Z amr\vanilare $
#| $Date: 2015-04-29 17:05:40 -0700 (Wed, 29 Apr 2015) $
#| $Author: amr\vanilare $
#| $Revision: 172 $
#+----------------------------------------------------------------------------+
#| TODO:
#|      *  Add LCPs >= LCP5
#+----------------------------------------------------------------------------+

"""
    Implement SIV Launch Control Policies as described on SIV Wiki Site:

        http://pcevwiki.amr.corp.intel.com/wiki/LT-SX/LaunchControlPolicy
"""

# Standard libary imports
import os           as _os
import sys          as _sys
import re           as _re
import logging      as _logging
from optparse import OptionParser

## Global Variables/Constants
bDebug                  = False
nOutputWidth            = 80
__version__             = "$Rev: 172 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())

# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDebug): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../../Generic/NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
if (bDebug): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDebug):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities
import GrubForceSelectUntrustedLinux as _GrubForceSelectUntrustedLinux

#  Since we may want to import functionality from this script into another script,
#  only create the Logger instance if this is executing as a script and not being
#  imported as a module
if __name__ == '__main__':
    lLogger = _ValToolsUtilities.setupLogger(bDebug, sLogfileName)

sLcpHashFileCONST       =   "lcp.hash"
sLcpElementFileCONST    =   "lcp.element"
sLcpListFileCONST       =   "lcp.list"
sLcpDataFileCONST       =   "lcp.data"     #  Important that this ends with ".data" as a suffix
sLcpPolicyFileCONST     =   "lcp.policy"
sPcrsOutputFileCONST    =   "pcr00.data"
sGrubTbootMenuPathCONST =   "/usr/local/etc/grub.d/"
sGrubTbootMenuFileCONST =   "42_tboot"
sEncryptionPrivKeyCONST =   "rsa_privkey.pem"
sEncryptionPubKeyCONST  =   "rsa_pubkey.pem"
sTxtStatFile            =   "txtstatdata"
sBogusPCR1              =   "pcr01.data"
sBogusPCR2              =   "pcr02.data"
sBogusPCR3              =   "pcr03.data"
sBogusPCR4              =   "pcr04.data"
sBogusPCR5              =   "pcr05.data"
sBogusPCR6              =   "pcr06.data"
sBogusPCR7              =   "pcr07.data"
sBogusPCR8              =   "pcr08.data"


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
    parser.add_option("--debug", action="store_true", dest="Debug", 
                      default=False,
                      help="Enable debug output; don't actually execute commands")

    parser.add_option("--policy_num", action="store", dest="PolicyNum", 
                      type="choice", 
                      choices=[ "1",
                                "2",
                                "3",
                                "4",
                                "5",
                                "6",
                                "7",
                                "8",
                                "10",
                                "16"],
                      default="1",
                      help="Indicates the policy number to implement. See LCP\
                            descriptions for details on each policy.")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug  Option read as %s"  % oCmdlineOptions.Debug              )
    lLogger.debug("Policy Number Option read as %s" % oCmdlineOptions.PolicyNum    )

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Measuring the Launch Environment using input from specified source(s)
#|
#|  Inputs:     
#|              String indicating which elements to use in creating the hash
#|              [optional] Name of file in which to write the MLE Hash data
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def createMleHash(
                    sLoggingString, 
                    sLcpHashFile=sLcpHashFileCONST, 
                    bDebug=False
                 ):
    #  Measuring the Launch Environment
    #  i.e. create a hash from certain elements of tboot.gz logfile
    sDescription    = "create a HASH from the TBOOT log file (measure the launch environment)."
    sCommand        = "/usr/sbin/lcp_mlehash -c 'logging=%s' /boot/tboot.gz" % sLoggingString
    try:
        sCmdOutput      = _ValToolsUtilities.returnOsCommand( lLogger, sCommand, sDescription, 
                                                              bVerbose=True, bDoNotRun=bDebug)
    except Exception, eCommand:
        lLogger.error("Command to create MLE hash failed.  This is critical, so I'm done.")
        lLogger.error("Command Output was: %s" % eCommand)
        return 0

    #  Write the MLE Hash out to a file, as the next command accepts only
    #  file-based input for the MLE hash
    lLogger.info("Writing MLE Hash to output file: '%s'" % sLcpHashFile)
    with open(sLcpHashFile, "w") as fTbootHash:
        fTbootHash.write(sCmdOutput)
        fTbootHash.write("\n")

    #  Return 1 for success
    return 1


#+----------------------------------------------------------------------------+
#|  Create an LCP Policy Element
#|
#|  Inputs:     
#|              String indicating type of element
#|              String indicating policy element control value
#|              String indicating minimum SINIT version
#|              String indicating LCP hash input file
#|              [optional] String indicating element output file
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def createLcpElement(
                      sType                                   ,
                      sCtrl                                   ,
                      sSinitMinVer                            ,
                      sLcpHashFile                            ,
                      sLcpElementFile = sLcpElementFileCONST  ,
                      bMultiplePcrBogusValues    = False      ,
                      bDebug          = False
                    ):
    bSuccess        = False
    
    #  For LCP 7 and LCP 8 the SINIT Minimum Version should be calculated
    #  from ACM version obtained from the output of command execution of
    #  txt-stat. 
    sSinitOption = ""
    if (sSinitMinVer == "CurrentVersion" or sSinitMinVer == "NotCurrentVersion"):

        # If we want a BAD ACM version, we'll need this information later
        bCorruptAcmVersion  =   False
        if(sSinitMinVer == "NotCurrentVersion"):
            bCorruptAcmVersion  =   True

        # Get the output from txtstat and store it in a variable
        sDescription    = "get the acm_version from txt-stat(needed to calculate SinitMinVer)"
        sCommand        = "/usr/local/sbin/txt-stat"
        try:
            sCmdOutput  = _ValToolsUtilities.returnOsCommand( lLogger, sCommand, sDescription, 
                                                              bVerbose=False, bDoNotRun=bDebug)
        except Exception, eCommand:
            lLogger.error("Command to run txtstat failed.  This is critical, so I'm done.")
            lLogger.error("Command Output was: %s" % eCommand)
            return 0

        # Compile pattern to search for ACM version text
        pAcm = _re.compile("acm_ver: (\d+)", _re.MULTILINE)
        # Extract the digits associated with ACM version text
        mAcm = pAcm.search(sCmdOutput)
        # If we got no match, we're in trouble
        if mAcm == None:
            lLogger.error("Didn't find an ACM version in the output of txt stat.  Can't continue...")
            return 0
        # If we got a match, inform user and proceed
        else:
            nSinitMinVer= int(mAcm.group(1))
            lLogger.info("Found ACM version; its value is %d" % nSinitMinVer)

        # If we want the min version to NOT be the current version, add 1 to the current version
        if(bCorruptAcmVersion):
            nSinitMinVerBad = nSinitMinVer + 1
            lLogger.info("Target ACM version specified to be *NOT* the current version.")
            lLogger.info("    Changing expected ACM version to (current version + 1) : %d" % nSinitMinVerBad)
            nSinitMinVer = nSinitMinVerBad

        # Convert the decimal version to a string that's the hexadecimal version
        sSinitMinVer = hex(nSinitMinVer)

    #  If SINIT Minimum Version is not specified, don't include the option
    #  in the command line at all - it doesn't apply to some element types 
    if not (sSinitMinVer == None):
        sSinitOption = "-minver %s" % sSinitMinVer
    if(bMultiplePcrBogusValues): 
    #Bogus PCRs for LCP 16.
        BogusPCRs=["PCR-01: AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA\n","PCR-02: BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB\n","PCR-03: CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC\n", "PCR-04: DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD\n","PCR-05: EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE\n","PCR-06: A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1\n","PCR-07: B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1\n","PCR-08: C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1 C1\n"]  
        with open(sBogusPCR1,"w") as BogusPcr1:
            BogusPcr1.write(BogusPCRs[0])
        with open(sBogusPCR2,"w") as BogusPcr2:
            BogusPcr2.write(BogusPCRs[1])
        with open(sBogusPCR3,"w") as BogusPcr3:
            BogusPcr3.write(BogusPCRs[2])
        with open(sBogusPCR4,"w") as BogusPcr4:
            BogusPcr4.write(BogusPCRs[3])
        with open(sBogusPCR5,"w") as BogusPcr5:
            BogusPcr5.write(BogusPCRs[4])
        with open(sBogusPCR6,"w") as BogusPcr6:
            BogusPcr6.write(BogusPCRs[5])
        with open(sBogusPCR7,"w") as BogusPcr7:
            BogusPcr7.write(BogusPCRs[6])
        with open(sBogusPCR8,"w") as BogusPcr8:
            BogusPcr8.write(BogusPCRs[7])
    #  Set up the command and run it
 
    sDescription    = "create a TXT Policy MLE Element."
    sCommand        = "/usr/sbin/lcp_crtpolelt --verbose --create --type %s --ctrl %s %s --out ./%s ./%s ./%s ./%s ./%s ./%s ./%s ./%s ./%s ./%s" % (
                           sType               ,
                           sCtrl               ,
                           sSinitOption        ,
                           sLcpElementFile     ,
                           sLcpHashFile        ,
                           sBogusPCR1          ,
                           sBogusPCR2          , 
                           sBogusPCR3          ,
                           sBogusPCR4          ,
                           sBogusPCR5          ,
                           sBogusPCR6          ,
                           sBogusPCR7          ,
                           sBogusPCR8          
                      )

    #  Set up the command and run it
    if(not(bMultiplePcrBogusValues)):
        sDescription    = "create a TXT Policy MLE Element."
        sCommand        = "/usr/sbin/lcp_crtpolelt --verbose --create --type %s --ctrl %s %s --out ./%s ./%s" % (
                               sType               ,
                               sCtrl               ,
                               sSinitOption        ,
                               sLcpElementFile     ,
                               sLcpHashFile   
                          )
 
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    return bSuccess


#+----------------------------------------------------------------------------+
#|  Create a TXT Policy List from the policy element file provided
#|
#|  Inputs:     
#|              [optional] String indicating policy list output file
#|              [optional] String indicating policy element input file
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def createPolicyList(
                      sLcpListFile    = sLcpListFileCONST,
                      sLcpElementFile = sLcpElementFileCONST,
                      bDebug          = False
                    ):
    #  Set up the command and run it
    bSuccess        = False
    sCommand        = "/usr/sbin/lcp_crtpollist --verbose --create --out ./%s ./%s" % (
                        sLcpListFile, sLcpElementFile
                    )
    sDescription    = "create the TXT Policy List from the TXT Policy MLE Element."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    return bSuccess


#+----------------------------------------------------------------------------+
#|  Create a TXT policy (and policy data file) from the data in the 
#|  list files provided 
#|  
#|
#|  Inputs:     
#|              String indicating policy type
#|              String indicating policy control value
#|              [optional] String indicating policy output file 
#|              [optional] String indicating policy data input file
#|              [optional] String indicating policy list input files
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def createPolicy(
                      sType          = "list",
                      sCtrl          = 0x2,
                      sLcpPolicyFile = sLcpPolicyFileCONST,
                      sLcpListFile   = sLcpListFileCONST,
                      sLcpDataFile   = sLcpDataFileCONST,
                      bDebug         = False
                 ):
    bSuccess        = False
    #  Set up the command and run it
    sDescription    = "create the TXT Policy and its associated data file"
    sCommand        = "/usr/sbin/lcp_crtpol2 --verbose --create --type %s --ctrl %s --pol ./%s --data ./%s ./%s" % (
                      sType             ,
                      sCtrl             ,
                      sLcpPolicyFile    ,
                      sLcpDataFile      ,
                      sLcpListFile   
                    )
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    return bSuccess



#+----------------------------------------------------------------------------+
#|  Read the value of PCR00 and write it to a local file
#|
#|  Inputs:     
#|              [optional] Boolean indication of whether to use real PCR
#|                         data or use a bogus value (all 0xFFs)
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def readPcr00(
                bPcrBogusValue  = False, 
                bDebug          = False
             ):
    bSuccess    = False
    sPcr00Value = "I didn't find it"

    lLogger.info("Attempting to get value for PCR-00")
    #  If we want a bogus value for our PCR data, then substitute it here
    if bPcrBogusValue:
        sPcr00Value = "PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF\n" 
        lLogger.info("Bogus value requested to be used for PCR-00 data.")
        lLogger.info("Not using actual register data; using this instead: \n'%s'" % sPcr00Value)
    #  Find the actual PCR00 value if we need it
    else:
        lLogger.info("Actual PCR-00 data requested, so attempting to get it.")
        #  Find the file in the Linux filesystem that has PCR data in it
        sDescription    = "find the location of the pcrs file within /sys/devices"
        sCommand        = "find /sys/devices/ -name pcrs"
        try:
            sPcrsInputFile      = _ValToolsUtilities.returnOsCommand( lLogger, sCommand, sDescription, 
                                                                      bVerbose=True, bDoNotRun=bDebug)
        except Exception, eCommand:
            lLogger.error("Command to create find the pcrs file failed.  This is critical, so I'm done.")
            lLogger.error("Command Output was: %s" % eCommand)
            return 0
        
        #  Check that the path we get matches the general location we expect
        if not _re.match("/sys/devices/", sPcrsInputFile):
            lLogger.error("Unable to interpret output of previous command. Can't continue.")
            return 0
        
        #  Find the value of PCR-00
        lLogger.info("Attempting to read file: '%s'" % sPcrsInputFile)
        with open(sPcrsInputFile, "r") as fPcrsInputFile:
            #  Read the PCRs file
            lPcrsData = fPcrsInputFile.readlines()
        
            #  Look through the contents of the file for the line containing "PCR-00: "
            for sLine in lPcrsData:
                if _re.match("PCR-00: ", sLine):
                    sPcr00Value = sLine
                    #  Strip off the text prefix at the beginning of the line
                    #  Remove this line of code, as it seems crtpolelt expects a 
                    #  text prefix in front of the PCR00 data.  Uncomment this
                    #  line if it ever changes.
                    #sPcr00Value = _re.sub("^PCR-00: ", "", sPcr00Value)

    #  If we didn't find a usable value for PCR-00 and we need it, that's bad
    if (sPcr00Value == "I didn't find it"):
        lLogger.error("I found the PCRs file, but it didn't have a PCR-00 entry in it.  I'm done.")
        return 0

    #  Write PCR-00 value to local file for use later
    with open(("./%s" % sPcrsOutputFileCONST), "w") as fPcrsOutputFile:
        fPcrsOutputFile.write(sPcr00Value)

    bSuccess = 1

    return bSuccess

#+----------------------------------------------------------------------------+
#|  Reads the GRUB menu source file from /usr/local/etc/grub.d/42_tboot and 
#|  modifies the "TBOOT> TBOOT LCP" entry to use the LCP policy DATA file we
#|  just created
#|
#|  Inputs:     
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def modifyGrubMenuEntry(bDebug=False):
    bSuccess                = False
    bNeedToModifyGrubFile   = False
    bFoundTbootlcpSection   = False

    sOldGrubTbootMenuFile   = "%s%s"     % (sGrubTbootMenuPathCONST, sGrubTbootMenuFileCONST)
    sNewGrubTbootMenuFile   = "./%s.new" % (sGrubTbootMenuFileCONST)

    lLogger.info("Attempting read Grub Menu source file and modify if necessary.")

    #  Open the new local file to create a modified version of the file
    lLogger.info("    Attempting to write file: '%s'" % sNewGrubTbootMenuFile)
    with open(sNewGrubTbootMenuFile, "w") as fNewGrubTbootMenuFile:
        #  Open the existing file and loop through its lines
        lLogger.info("    Attempting to read file: '%s'" % sOldGrubTbootMenuFile)
        with open(sOldGrubTbootMenuFile, "r") as fOldGrubTbootMenuFile:
            #  Loop through the lines of the existing file, looking for the
            #  line we may need to modify
            for sOldLine in fOldGrubTbootMenuFile:
                sOldLine = sOldLine.rstrip()
                sNewLine = sOldLine
                if _re.match('menuentry \'TBOOT LCP\'', sOldLine):
                    bFoundTbootlcpSection   = True
                if bFoundTbootlcpSection and _re.match('\s*module.*\.data', sOldLine):
                    lLogger.info("    Found menu file line with LCP data entry: \n    %s" % sOldLine)
                    rExpectedLine = _re.compile('\s*module.*%s' % _re.escape(sLcpDataFileCONST))
                    if rExpectedLine.match(sOldLine):
                        lLogger.info("    Existing menu file line matches target; no new menu file necessary.")
                    else:
                        lLogger.info("    Existing menu file line does not match target; modifying line in new file.")
                        sNewLine = _re.sub('\w+\.data', sLcpDataFileCONST, sNewLine)
                        lLogger.info("    Modified menu file line with LCP data entry to be: \n    %s" % sNewLine)
                        bNeedToModifyGrubFile   = True
                fNewGrubTbootMenuFile.write("%s\n" % sNewLine)
    lLogger.info("    Done reading/writing Grub Menu source file.")

    #  If we've created a new Grub Menu source file that's the same as the
    #  existing one, we're done
    if not bNeedToModifyGrubFile:
        bSuccess = True
    #  If we've created a new Grub Menu source file that's different from the
    #  existing one, we need to back up the old one and copy the new one to the 
    #  standard location.
    else:
        #  Backup old file
        sCommand        = "cp -f %s ./%s.backup" % (sOldGrubTbootMenuFile, sGrubTbootMenuFileCONST)
        sDescription    = "backup the current copy of the Grub Menu tboot source file."
        bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                           bCriticalStep=True, bVerbose=True,
                                                           bDoNotRun=False)
        #  If the backup failed, inform user and DO NOT overwrite existing file
        if (not bSuccess): 
            lLogger.error("Unable to backup current copy of the Grub Menu tboot source file.")
            lLogger.error("This is a required step, so I will not proceed with writing the new")
            lLogger.error("file to the existing location.")
        else:
            #  Copy newly-created file to standard location
            sCommand        = "cp -f %s %s" % (sNewGrubTbootMenuFile, sOldGrubTbootMenuFile)
            sDescription    = "copy new Grub Menu tboot source file to standard location."
            bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                               bCriticalStep=True, bVerbose=True,
                                                               bDoNotRun=False)
            if (not bSuccess): 
                lLogger.error("Unable to copy the Grub Menu tboot source file to the standard location.")

    #  Return indicator for success
    return bSuccess


#+----------------------------------------------------------------------------+
#|  Encrypt the Policy List via OpenSSL RSA Encryption
#|
#|  Inputs:     
#|              [optional] Encryption strength (bits)
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def encryptPolicyList(nEncryptBits=2048, bDebug=False):
    bSuccess        = False

    #  Create a Private Key
    sBaseCommand    = "sudo /usr/bin/openssl"
    sCommand        = "%s genrsa -out ./%s %d" % (
                                                    sBaseCommand,
                                                    sEncryptionPrivKeyCONST, 
                                                    nEncryptBits
                                                 )
    sDescription    = "create the OpenSSL RSA private key."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0


    #  Create a Public Key
    sBaseCommand    = "sudo /usr/bin/openssl"
    sCommand        = "%s rsa -pubout -in ./%s -out ./%s" % (
                                                                sBaseCommand,
                                                                sEncryptionPrivKeyCONST,
                                                                sEncryptionPubKeyCONST
                                                            )
    sDescription    = "create the OpenSSL RSA public key."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0


    #  Encrypt the List
    sBaseCommand    = "sudo /usr/sbin/lcp_crtpollist"
    sCommand        = "%s --sign --pub ./%s --priv ./%s --out ./%s" % (
                                                                        sBaseCommand,
                                                                        sEncryptionPubKeyCONST,
                                                                        sEncryptionPrivKeyCONST,
                                                                        sLcpListFileCONST
                                                                      )
    sDescription    = "encrypt the LCP Policy List with the OpenSSL RSA public/private keys."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0


    #  Return indicator for success
    return True


#+----------------------------------------------------------------------------+
#|  Set up a Launch Control Policy
#|
#|  Inputs:     
#|              String indicating what type of TXT element to use
#|              String indicating "logging" parameter for mlehash tool
#|              [optional] String indicating minimum SINIT version (or None)
#|              [optional] Boolean indication of whether to use real PCR
#|                         data or use a bogus value (all 0xFFs)
#|              [optional] Boolean indication of whether we're in debug mode
#|
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def createLaunchControlPolicy(
                                sTxtElementType             , 
                                sMleHashLogging             ,
                                bEncryptPolicyList  = False ,
                                nEncryptPolicyBits  = 2048  ,
                                sSinitMinVersion    = None  , 
                                bPcrBogusValue      = False , 
                                bCtrl               = False ,
                                bMultiplePcrBogusValues=False,
                                bDebug=False
                             ):
    #  Read the value of PCR00 and write it to a file to use later
    bSuccess = readPcr00(bPcrBogusValue=bPcrBogusValue, bDebug=bDebug)
    if (not bSuccess): return 0

    #  Measure the Launch Environment using input from specified source(s)
    bSuccess = createMleHash(
                                sLoggingString=sMleHashLogging, 
                                bDebug=bDebug
                            )
    if (not bSuccess): return 0

    #  Choose which source data we'll use for the LCP Hash
    sLcpHashFile = sLcpHashFileCONST
    if (sTxtElementType == "pconf"):
        sLcpHashFile = sPcrsOutputFileCONST
    if (bMultiplePcrBogusValues):
        sLcpHashFile = sPcrsOutputFileCONST
        bSuccess = createLcpElement(sTxtElementType, "0x00",sSinitMinVersion,sLcpHashFile,bMultiplePcrBogusValues=True,bDebug=bDebug)
    #  Create an LCP Policy Element 
    else:
        bSuccess = createLcpElement(sTxtElementType, "0x00", sSinitMinVersion, sLcpHashFile,bDebug=bDebug)
    
    if (not bSuccess): return 0

    #  Create a TXT Policy List from the policy element
    #  created in the previous step
    bSuccess = createPolicyList(bDebug=bDebug)
    if (not bSuccess): return 0

    #  If requested, encrypt the Policy List before creating the policy
    if (bEncryptPolicyList):
        bSuccess = encryptPolicyList(nEncryptBits=nEncryptPolicyBits)
    if (not bSuccess): return 0
    
    
    #  Create a TXT policy (and policy data file) from the data in the 
    #  list file created in the previous step if it LCP 10 , the Ctrl value 
    #  will be 0x0 , NPW bit is being modified .
    if (bCtrl):
        bSuccess = createPolicy("list", 0x0, bDebug=bDebug)
        if (not bSuccess): return 0
    else:
    #  Create a TXT policy (and policy data file) from the data in the 
    #  list file created in the previous step
        bSuccess = createPolicy("list", 0x2, bDebug=bDebug)
        if (not bSuccess): return 0

    #  Write the newly created policy to the TPM
    #       -i:  index value
    #       -f:  policy filename
    #       -p:  password 
    sCommand        = "/usr/sbin/lcp_writepol -i owner -f ./%s -p ownerauth" % (sLcpPolicyFileCONST)
    sDescription    = "write the newly created policy to the Trusted Platform Module (TPM)."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0

    #  Copy policy data to boot directory
    sCommand        = "cp ./%s /boot/%s" % (sLcpDataFileCONST, sLcpDataFileCONST)
    sDescription    = "copy the newly created policy file to /boot directory."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0

    #  Modify the default GRUB boot selection to be "TBOOT>TBOOT LCP"
    sCommand        = 'sed -i \'s/GRUB_DEFAULT=.*/GRUB_DEFAULT="TBOOT>TBOOT LCP"/\' /usr/local/etc/default/grub'
    sDescription    = "Modify the default GRUB boot selection to be 'TBOOT>TBOOT LCP'"
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0

    #  Modify the file used to create the Grub Menu
    bSuccess = modifyGrubMenuEntry()
    if (not bSuccess): return 0


    #   Run grub-mkconfig to generate a new grub.cfg file since we just modified
    #   some of the grub parameters
    #
    #   NOTE: about the grub.cfg file
    #
    #           It is automatically generated by grub-mkconfig using templates
    #           from /usr/local/etc/grub.d and settings from 
    #           /usr/local/etc/default/grub
    sCommand        = "sudo /usr/local/sbin/grub-mkconfig -o /boot/grub/grub.cfg"
    sDescription    = "generate a new grub.cfg file since we just modified some of the grub parameters."
    bSuccess        = _ValToolsUtilities.runOsCommand( lLogger, sCommand, sDescription, 
                                                       bCriticalStep=True, bVerbose=True,
                                                       bDoNotRun=bDebug)
    if (not bSuccess): return 0

    #   Need to ensure that the NVRAM Bit that SIV's custom Grub menu
    #   examines on each boot is set to DISABLE recovery mode; otherwise
    #   the system will not invoke TBOOT on the next boot cycle
    lLogger.info("Running SIV function to disable Grub recovery mode via BIOS scratchpad.")
    bSuccess    = _GrubForceSelectUntrustedLinux.writeNvramIfNecessary(lLogger=lLogger, bEnable=False, bDisable=True)
    if bSuccess:
        lLogger.info("    Grub Recovery Mode successfully disabled")
    else:
        lLogger.error("    Grub Recovery Mode NOT disabled.  The system will not likely invoke TBOOT next time.")
        return 0


    #   We're done, so return a 1 to indicate success
    return 1




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

   
    lLogger.info("Policy specified as %02d ...Creating...." % int(oCmdlineOptions.PolicyNum))

    if (oCmdlineOptions.PolicyNum == "1"):
        lLogger.info("")
        lLogger.info("LCP1:  Platform Owner Measured Launch Environment")
        lLogger.info("")
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion="0", 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "2"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle",
                                                            sMleHashLogging="com1",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion="0", 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "3"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="pconf",
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion=None, 
                                                            bPcrBogusValue=False, 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "4"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="pconf",
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion=None, 
                                                            bPcrBogusValue=True, 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "5"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=True,
                                                            nEncryptPolicyBits=2048,
                                                            sSinitMinVersion="0", 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "6"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=True,
                                                            nEncryptPolicyBits=1024,
                                                            sSinitMinVersion="0", 
                                                            bDebug=oCmdlineOptions.Debug
                                                      )
    elif (oCmdlineOptions.PolicyNum == "7"):
        bErrorsOccured = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion="CurrentVersion", 
                                                            bDebug=oCmdlineOptions.Debug

                                                       )
    elif (oCmdlineOptions.PolicyNum == "8"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion="NotCurrentVersion", 
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
    elif (oCmdlineOptions.PolicyNum == "10"):
        bErrorsOccurred = not createLaunchControlPolicy(
                                                            sTxtElementType="mle", 
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
							                                sSinitMinVersion="0",
                                                            bCtrl=True,
                                                            bDebug=oCmdlineOptions.Debug
                                                       )
   
    elif (oCmdlineOptions.PolicyNum == "16"):
        bErrorsOccurred = not createLaunchControlPolicy( 
                                                            
                                                            sTxtElementType="pconf",
                                                            sMleHashLogging="serial,vga,memory",
                                                            bEncryptPolicyList=False,
                                                            sSinitMinVersion=None, 
                                                            bPcrBogusValue=False,
                                                            bMultiplePcrBogusValues=True, 
                                                            bDebug=oCmdlineOptions.Debug
                                                        )
    else:
        lLogger.info("--policy option set to '%s'" % oCmdlineOptions.PolicyNum)
        lLogger.info("    I don't know how to implement that policy.")
        bErrorsOccurred = True

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


