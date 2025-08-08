#!/usr/bin/env python
############################################################################
# INTEL CONFIDENTIAL
# Copyright 2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corp-
# oration or its suppliers and licensors. The Material may contain trade
# secrets and proprietary and confidential information of Intel Corpor-
# ation and its suppliers and licensors, and is protected by worldwide
# copyright and trade secret laws and treaty provisions. No part of the
# Material may be used, copied, reproduced, modified, published, uploaded,
# posted, transmitted, distributed, or disclosed in any way without
# Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellect-
# ual property right is granted to or conferred upon you by disclosure or
# delivery of the Materials, either expressly, by implication, inducement,
# estoppel or otherwise. Any license under such intellectual property
# rights must be express and approved by Intel in writing.
############################################################################
# $Id$
# $Date$
# $Author$
# $Revision$
############################################################################
#This script Enables the recovery of System.


########################### Standard Library imports #######################
import subprocess
import time
import os
import logging

################################ Global Variables###########################
nOUTPUT_WIDTH = 80
sVERSION      = "$$".replace("$Rev:","").replace("$","").strip()
sSTART_TIME   = time.asctime(time.localtime())
sSCRIPTNAME   = os.path.basename(__file__)
sLOGFILE_NAME = sSCRIPTNAME + ".log"


############################# Function Definitions #########################
def LogDelimiter():
    logger.info("*" * nOUTPUT_WIDTH)


###################### Setup of Logger for Output Logging ##################

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG) # Uncomment for debug output 

# Create formatter  e.g. "[   ERROR] This is an error message"
#     levelname has a width of 8 to accommodate the largest string: CRITICAL
formatter = logging.Formatter('[%(levelname)8s] %(message)s')

# Create console handler 
#     set formatter to object above
shConsoleHandler = logging.StreamHandler()
shConsoleHandler.setFormatter(formatter)

# Create log file handler 
#     set formatter to object above
fhLogHandler = logging.FileHandler(sLOGFILE_NAME, "w")
fhLogHandler.setFormatter(formatter)

# Add ConsoleHandler and LogHandler to logger
logger.addHandler(shConsoleHandler)
logger.addHandler(fhLogHandler)

#---------------------------------------------------------------------------
#    XX     XX  XXX      XXXXX  XX   XXXX
#     X     X     X        X     X i    X
#     XX   XX    X X       X     XX    X
#     XX   XX    X X       X     X X   X
#     X X X X   X   X      X     X X   X
#     X X X X   X   X      X     X  X  X
#     X  X  X   XXXXX      X     X   X X
#     X  X  X  X     X     X     X   X X
#     X     X  X     X     X     X    XX
#    XXX   XXXXXX   XXX  XXXXX  XXXX   X
#---------------------------------------------------------------------------
def main():
    nErrorsDetected = 0
    
    #Startup Banner
    LogDelimiter()
    logger.info(" %s(%s) started on %s" % (sSCRIPTNAME, sVERSION, sSTART_TIME))
    LogDelimiter()
    
    #  System call writing value 0x71 to CMOS register at offset 0x70
    os.system("outb 0x70 0x71")
    
    # Read the value of 0x70 at offset 0x71
    a=subprocess.Popen(["inb","0x71"],stdout=subprocess.PIPE)

    # Removes the new character end of the standard output.
    out=a.stdout.read().rstrip('\n')
    
    #Checking the last bit of value at offset 0x71. 
    if (int(out) & (0x01) == 0x01):

    # Enters here if the system is already Enabled i.e. the last bit at Address 0x71 is 'one'
       	logger.info("It is in Recovery mode....")
    
    else:

    # Current bit value is 'zero' , its needs to be one to Enable Recovery.
	logger.info("Enabling Recovery of System.....")

    # Performing 'or' operation with 0x01 to change the lastbit from zero to one.
    	EnableValue= (int(out) | 0x01)
    
    #  Writting the new value with last bit changed to one at address 0x71.
	subprocess.Popen(["outb","0x71",str(EnableValue)])

    LogDelimiter()
    # Print each line of output from spUcodeData, indenting by "    "
   # for sLine in iter(spUcodeData.stdout.readline, ''):
    logger.info("Pass")
    LogDelimiter()
    
    # Indicate success
    logger.info("Script completed successfully!")
    return 1
    
    
    
####################################################################################

if __name__ == '__main__':
    if main():
        exit(0)  # zero exit status means script completed successfully
    else:
        exit(1)  # non-zero exit status means script did not complete successfully




