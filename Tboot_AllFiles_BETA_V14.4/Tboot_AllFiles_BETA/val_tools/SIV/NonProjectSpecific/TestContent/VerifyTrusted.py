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
#| $Id: VerifyTrusted.py 136 2015-02-03 00:52:09Z amr\egross $
#| $Date: 2015-02-02 16:52:09 -0800 (Mon, 02 Feb 2015) $
#| $Author: amr\egross $
#| $Revision: 136 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    This script checks the status and error status registers in the PCH
    that are associated with LT-SX/TXT and determines if the system has
    successfully booted in a trusted mode
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
__version__             = "$Rev: 136 $".replace("$Rev:","").replace("$","").strip()
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

#  Since we may want to import functionality from this script into another script,
#  only create the Logger instance if this is executing as a script and not being
#  imported as a module
if __name__ == '__main__':
    lLogger = _ValToolsUtilities.setupLogger(bDebug, sLogfileName)





#+----------------------------------------------------------------------------+
#|  Section for SIV-specific constants and technical definitions
#+----------------------------------------------------------------------------+

# From Patsburg PCH C-Spec 27.5.1 (LT Registers: Register Decode):
"""
LT transactions are divided into three categories: public, private and LT;
based on how they are decoded in the system. Public registers are always
available under all conditions and are done as memory transactions in the
0xFED3_xxxx range. Private registers are accessible only when Private.Open.STS
is '1' and are done as memory transactions in the 0xFED2_xxxx range. When
Private.Open.STS='0', then private registers must not allow writes or commands
to be decoded. Memory reads to the 0xFED2_xxxx range are always decoded,
independent of the Private.Open.STS bit.  Note that the register is defined by
the 4 bit offset, such as ESTS at offset 0008. There are not 2 separate
registers, one at 0xFED2_0008 and another at 0xFED3_0008. Instead the first
nibble of the address determines the access rights to the single register.
"""
nLtPublicBar    =   0xFED30000
nLtPrivateBar   =   0xFED20000

# From Patsburg PCH C-Spec 27.5.3 (Table for Decode BB LTR/LTW Cycles)
dOffsetLt   = dict(
                    LT_STS       = 0x0000,
                    LT_ESTS      = 0x0008,
                    LT_EXISTS    = 0x0010,
                    LT_JOINS     = 0x0020,
                    LT_SPAD      = 0x00A0,
                    LT_DID       = 0x0110,
                    LT_FITSTATUS = 0x0340,
                    LT_E2STS     = 0x08F0
              )

#  Define Expected Values for various registers
#  These registers are defined in section 27.5.4 of the Patsburg C-Spec
dExpectedValue = {}

#  LT_STS Bits of Interest for typical trusted boot:
#  
#      16:14  Indicate whether Locality2:0 ranges are open (1) or closed (0)
#          7  Set to 1 when CMD.OPEN-PRIVATE is decoded and SENTER.DONE==1    
#          4  Indicates memory is unlocked when set to (1)
#          0  SENTER.DONE.STS - indicates JOINS==EXISTS (CPUs have joined MLE)
#  
#  Combining the bits of interest results in 0x0001_C091
dExpectedValue['LT_STS'] = 0x0001C091


#  LT_ESTS Bits of Interest for typical trusted boot:
#  
#      We expect no errors to be logged, so all bits should be zero!
#  
#  Combining the bits of interest results in 0x0000_0000
dExpectedValue['LT_ESTS'] = 0x00000000


#  LT_E2STS Bits of Interest for typical trusted boot:
#  
#      3  RESET.STS -     Indicates a reset was initiated from LT sources.
#                         Backed by RTC well, so value is preserved across
#                         almost all resets and power cycles.  A loss of RTC
#                         power (e.g. remove CMOS battery) or a RTEST# assertion
#                         is the only way to clear this bit.
#
#      2  BLOCK-MEM.STS - Indication from PCH to MCH that it should prevent 
#                         accesses to memory.  This bit is set if RTEST# is
#                         asserted or when SECRETS is written.
#      1  SECRETS.STS -   Indicates there are potential secrets in memory
#
#  
#  Combining the bits of interest results in 0x0000_0006 for the general case
#
#  NOTE: If there has been an improper shutdown of TBOOT and secrets might be
#  in memory on the next cycle, the LT-initiated warm reset on the following
#  boot will set the RESET.STS bit.
dExpectedValue['LT_E2STS']  = 0x00000006
nLtE2StsResetStsBit         = 3

#  Linux command 'txtstat' produces a large quantity of text output
#  There are several key tokens in this output that must be present
#  to consider it a successful trusted boot.  This is a list of those
#  text tokens.
lRequiredTxtStatLines   =   (
                                'TXT measured launch: TRUE',
                                'secrets flag set: TRUE'
                            )


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

    parser.add_option("--expect_ltreset", action="store_true", 
                      dest="ExpectLtReset", default=False,
                      help="Specifiy this option if the test scenario is\
                            expected to cause an LT Reset.  This causes the\
                            script to expect bit %d of the E2STS register to be\
                            set.  An example scenario would be a surprise reset\
                            where TBOOT was unable to shut down properly."
                            % nLtE2StsResetStsBit
    )

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Set global bDebug variable and logger mesaging level if necessary
    if (oCmdlineOptions.Debug):
        global bDebug
        bDebug = oCmdlineOptions.Debug
        lLogger.setLevel(_logging.DEBUG)

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Debug  Option read as %s"  % oCmdlineOptions.Debug        )
    lLogger.debug("ExpectLtReset read as %s" % oCmdlineOptions.ExpectLtReset )

    #  If we're expecting an LT Reset, modify the expected value for E2STS
    if (oCmdlineOptions.ExpectLtReset):
        lLogger.debug("LT_E2STS old expected value: 0x%08x" % dExpectedValue['LT_E2STS'])
        nBitMask = 0x1 << nLtE2StsResetStsBit
        lLogger.debug("ExpectLtReset bitmask was:   0x%08x" % nBitMask)
        dExpectedValue['LT_E2STS']  = dExpectedValue['LT_E2STS'] | nBitMask
        lLogger.debug("LT_E2STS new expected value: 0x%08x" % dExpectedValue['LT_E2STS'])

    #  Return options data structure
    return oCmdlineOptions

#+----------------------------------------------------------------------------+
#|  Check for expected value of the a register by reading its current value
#|      from MMIO space and then comparing it to an expected value
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def checkRegisterValue(sRegName, nRegAddr):

    #   Use Volatility to read memory address to accesses register of interest
    sDescription    = "execute MMIO read to PCH's %s register at 0x%08x" % (sRegName, nRegAddr)
    sCommand        = "sudo /usr/local/sbin/volatility -a 0x%x" % nRegAddr
    sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription)
    if (sCommandOutput == "returnOsCommand: Command Failure"):
        return False
    nCommandOutput = int(sCommandOutput, 16)

    #   Compare the actual value to the expected value
    if (nCommandOutput != dExpectedValue[sRegName]): 
        lLogger.error("    %s expected to be  0x%08x"  % (sRegName, dExpectedValue[sRegName]))
        lLogger.error("    %s actual was      0x%08x"  % (sRegName, nCommandOutput))
        lLogger.error("    %s register is not as expected....." % (sRegName))
        return False
    else:
        lLogger.info("    %s register was as expected (0x%08x)" % (sRegName, dExpectedValue[sRegName]))

    return True



#+----------------------------------------------------------------------------+
#|  Check all required criteria to confirm a successful trusted boot
#|
#|  TODO:  This function has grown a bit, and probably should be broken up into
#|         a few subfunctions to make it more readable
#|
#|  Inputs:     None
#|  Returns:    True on success; otherwise, False
#|
#+----------------------------------------------------------------------------+
def validateTrusted():
    bErrorsOccurred = False

    #   Check the output of TXTSTAT to ensure it contains the required text tokens
    #   that indicate a successful trusted boot.
    sCommand        = "sudo /usr/sbin/txt-stat"
    sDescription    = "to look for indications of a trusted boot in TXTSTAT output."
    if (bDebug):
        sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription, True)
    else:
        sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription, False)
    if (sCommandOutput == "returnOsCommand: Command Failure"):
        return False
    lLogger.info("Examining TXTSTAT output...")
    for sText in lRequiredTxtStatLines: 
        if sText not in sCommandOutput:
            lLogger.error("    [FAIL] Did not find text: '%s'" % sText)
            bErrorsOccurred = True
        else:
            lLogger.info("    [PASS] Found text: '%s'" % sText)

    #   Log the value of the LT_EXISTS register
    #   TODO: maybe add code later that compares this value against the 
    #         number of actual CPUs installed rather than blindly trusting its value
    nMmioAddress    = nLtPublicBar + dOffsetLt["LT_EXISTS"]
    sDescription    = "execute MMIO read to PCH's LT_EXISTS register at 0x%08x" % (nMmioAddress)
    sCommand        = "sudo /usr/local/sbin/volatility -a 0x%x" % nMmioAddress
    sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription)
    if (sCommandOutput == "returnOsCommand: Command Failure"):
        return False
    nExistsRegVal   = int(sCommandOutput, 16)
    if (nExistsRegVal == 0x0) :
        lLogger.error("LT_EXISTS register should not be 0x0000_0000.  Something is wrong.")
        lLogger.error("    Perhaps the platform is not LT-strapped?")
        bErrorsOccurred = True
    else:
        lLogger.info("LT_EXISTS register value:  0x%08x" % nExistsRegVal)
        dExpectedValue['LT_JOINS'] = nExistsRegVal

    # LT_JOINS Check
    #   This register contains a one-hot encoded value for all threads
    #   that have joined the MLE.  Ideally, it should match the contents of 
    #   the LT_EXISTS register, indicating that all threads have joined the MLE
    lLogger.info("Checking LT_JOINS Register Value...")
    lLogger.info("    It should be the same as the LT_EXISTS register value from above.")
    lLogger.info("    This indicates all availble threads have joined the MLE.")
    nMmioAddress = nLtPublicBar + dOffsetLt["LT_JOINS"]
    bCheckPass=checkRegisterValue("LT_JOINS", nMmioAddress)
    if (not bCheckPass): 
        bErrorsOccurred=True

    # LT_STS Check
    lLogger.info("Checking LT_STS Register Value...")
    nMmioAddress = nLtPublicBar + dOffsetLt["LT_STS"]
    bCheckPass=checkRegisterValue("LT_STS", nMmioAddress)
    if (not bCheckPass): 
        bErrorsOccurred=True

    # LT_ESTS Check
    lLogger.info("Checking LT_ESTS Register Value...")
    nMmioAddress = nLtPublicBar + dOffsetLt["LT_ESTS"]
    bCheckPass=checkRegisterValue("LT_ESTS", nMmioAddress)
    if (not bCheckPass): 
        bErrorsOccurred=True

    # LT_E2STS Check
    lLogger.info("Checking LT_E2STS Register Value...")
    nMmioAddress = nLtPublicBar + dOffsetLt["LT_E2STS"]
    bCheckPass=checkRegisterValue("LT_E2STS", nMmioAddress)
    if (not bCheckPass): 
        bErrorsOccurred=True

    #   Log the value of the LT_SPAD register
    nMmioAddress    = nLtPublicBar + dOffsetLt["LT_SPAD"]
    sDescription    = "execute MMIO read to PCH's LT_SPAD register at 0x%08x" % (nMmioAddress)
    sCommand        = "sudo /usr/local/sbin/volatility -a 0x%x" % nMmioAddress
    sCommandOutput  = _ValToolsUtilities.returnOsCommand(lLogger, sCommand, sDescription)
    if (sCommandOutput == "returnOsCommand: Command Failure"):
        return False
    nSpadRegVal   = int(sCommandOutput, 16)
    lLogger.info("LT_SPAD register value:  0x%08x" % nSpadRegVal)

    #   Finish up - let user know overall status and exit
    lLogger.debug("bErrorsOccurred Value: %d" % bErrorsOccurred)
    if (bErrorsOccurred):
        lLogger.error("One or more Trusted Boot checks failed......")
        lLogger.error("    Check above error messages for details.")
        return False
    else:
        lLogger.info("Verified.......Trusted Boot Confirmed!")

    return True
    #return 0




#+------------------------------------------------------------------------------+
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

    #  Execute main function - determine if we've booted trusted or not
    bErrorsOccurred = not validateTrusted()

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


