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

#Script compares current PCR register values with logged PCR registers
#This script takes log containing logged PCR values as INPUT
#TPM stores measurements in Platform Configuration Registers (PCRs)
#Platform elements of the trusted computing base (TCB), such as SINIT and launch control policy (LCP) are put into PCR 17 
#The MLE is extended into PCR 18
#A subset of BIOS initialization code that is in PCR 0


#############################Standard Library imports########################
import os
import subprocess
import sys
import filecmp
######## Function Definition##############
def checkpcrnpw():

	filename=sys.argv[1]
	print '                 Getting Current Values of PCR registers.......       '
	os.system("cat `find /sys/devices/ -name pcrs` | grep -e PCR-00 > ./pcrs.new")
	os.system("cat `find /sys/devices/ -name pcrs` | grep -e PCR-17 >> ./pcrs.new")
	os.system("cat `find /sys/devices/ -name pcrs` | grep -e PCR-18 >> ./pcrs.new")
	print '			Comparing with user input file........	'

	if (filecmp.cmp('pcrs.new',filename)):
		print 'Passed....PCR register values  match!'
		return 0
	else:
		print 'Failed.....PCR register values do not match!'	
		return 1

####### Main
def main():
	return checkpcrnpw()

if __name__ == '__main__':
	if main():
		exit(0)
	else:
		exit(1)

