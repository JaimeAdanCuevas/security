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
#i
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
#This script releases PS index in TPM


########################### Standard Library imports #######################
import subprocess
import time
import os
import logging

################################ Global Variables###########################
nOUTPUT_WIDTH = 80
PSindex="0x50000001"
sVERSION      = "$Rev: 24 $".replace("$Rev:","").replace("$","").strip()
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
#     X     X     X        X     X     X
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
    if(os.system("tpmnv_getcap | grep 0x50000001")!=0):
        print "PS index already released...."
    else:		    
    	TpmnvGetcapValue=subprocess.Popen(["tpmnv_getcap"],stdout=subprocess.PIPE)
    	tpmnv= TpmnvGetcapValue.stdout.read()
    	if PSindex in tpmnv:
    		release=os.system("tpmnv_relindex -i 0x50000001 -p ownerauth")
        	if release == 0:
        		print ' Successfully released PSindex......'
        	else:
                	print ' Failed releasing PSindex.......'
                	return 0

    LogDelimiter()
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



