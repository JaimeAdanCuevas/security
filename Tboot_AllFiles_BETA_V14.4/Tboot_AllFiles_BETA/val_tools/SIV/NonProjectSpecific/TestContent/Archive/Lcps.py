#!/usr/bin/env python
#+-------------------------------------------------------------------------+
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
#| $Id: lcp.py 68 2014-11-24 23:56:57Z amr\vanilare $
#| $Date: 2014-11-24 15:56:57 -0800 (Mon, 24 Nov 2014) $
#| $Author: amr\vanilare $
#| $Revision: 68 $
#+----------------------------------------------------------------------------+
#| TODO:
#|   *  
#+----------------------------------------------------------------------------+

"""
    Script implements LCP 1 policy
"""

# Standard libary imports
import os      as _os
import os
import sys     as _sys
import re      as _re 
import logging as _logging
from optparse import OptionParser
import subprocess
import shlex as _shlex
## Global Variables/Constants
bDEBUG                  = 0
nOutputWidth            = 80
__version__             = "$Rev: 68 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
tboot_hash=open("./tboot_hash","w")
tboot_bad_hash=open("./tboot_bad_hash","w")
pcr0=open("./pcr0","w")
# val_tools Utilities Import - gotta find it first!
sScriptPath = _os.path.dirname(__file__)
if (bDEBUG): 
    print "ScriptPath:                  %s" % sScriptPath
sUtilitiesPath = sScriptPath + "/../../../Generic/NonProjectSpecific/Utilities"  #  <--- make sure this is the correct relative path!
if (bDEBUG): 
    print "ValToolsUtilsPath:           %s" % sUtilitiesPath
sUtilitiesPath =  _os.path.normpath(sUtilitiesPath)
if (bDEBUG):
    print "NormalizedValToolsUtilsPath: %s" % sUtilitiesPath
_sys.path.append(sUtilitiesPath)
import ValToolsUtilities as _ValToolsUtilities

lLogger                 = _ValToolsUtilities.setupLogger(bDEBUG, sLogfileName)


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
    parser.add_option("--policy", action="store", dest="Policy", 
                      type="choice", choices=["1","2", "3","4","5","6","7","8","9","10","15","16","18","19","20","21","25"], default="2",
                      help="Sample option description")

    #  Process the actual command line and split it into options and arguments
    (oCmdlineOptions, aArgs) = parser.parse_args()

    #  Debug output to indicate what the results of command line processing are
    lLogger.debug("Sample Option read as %s" % oCmdlineOptions.Policy    )

    #  Return options data structure
    return oCmdlineOptions
#+----------------------------------------------------------------------------+
#|  Function To Print Generic Finishing Banner
#|
#|  Inputs:     None
#|  Returns:    1 on success; otherwise, 0
#|
#+----------------------------------------------------------------------------+
def lcp_any():
         print "\n"
         print " **********************************LcpAny**********************************"
	 Success=subprocess.call(["/usr/sbin/lcp_crtpol2","--create","--type","any","--ctrl","0x02","-pol","./lcp_any.pol"])
	 if (Success != 0): 
	 	lLogger.error(" LCP_ANY : Failed Running /usr/sbin/lcp_crtpol2")
		return 0
	 Success=subprocess.call(["/usr/sbin/lcp_writepol","-i","owner","-f","./lcp_any.pol","-p","ownerauth"])
         if (Success != 0):
		lLogger.error(" LCP_ANY : Failed Running /usr/sbin/lcp_writepol,Owner")
         	return 0
	 Success=subprocess.call(["/usr/sbin/lcp_writepol","-i","default","-f","./lcp_any.pol","-p","ownerauth"])
         if (Success != 0):
		lLogger.error(" LCP_ANY : Failed Running /usr/sbin/lcp_writepol,default")
		return 0
	 Success=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT'/g","/usr/local/etc/default/grub"])
	 if (Success != 0):
		lLogger.error(" LCP_ANY : Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT'/g,/usr/local/etc/default/grub")
	        return 0
	 Success=subprocess.call(["grub-mkconfig","-o","/boot/grub/grub.cfg"])
	 if (Success != 0):
		lLogger.error(" LCP_ANY : Failed Running grub-mkconfig,-o,/boot/grub/grub.cfg")
		return 0
	 else:
		lLogger.info("Successfully executed LCP_ANY")
		return 1

def releasePO():
	print"\n Running Release PO index"
	lLogger.info("Running tpmnv_getcap | grep 0x40000001 ")
	if(os.system("tpmnv_getcap | grep 0x40000001")!=0):
        	lLogger.info("PO index already released....")
    	else:
    		TpmnvGetcapValue=subprocess.Popen(["tpmnv_getcap"],stdout=subprocess.PIPE)
    		tpmnv= TpmnvGetcapValue.stdout.read()
		P0index="0x40000001"
    		if P0index in tpmnv:
    			release=os.system("tpmnv_relindex -i 0x40000001 -p ownerauth")
        		if release == 0:
        			print ' Successfully released P0index.......'
				return 1
        		else:
                		print ' Failed releasing P0index.......'
                		return 0
		else:
			lLogger.error("PO index does not exist")
			return 0

def lcp_ps_any():
         print "\n"
         print " **********************************LcpPSAny**********************************"
	 Success=subprocess.call(["/usr/sbin/lcp_crtpol2","--create","--type","any","--ctrl","0x02","-pol","./lcp_any.pol"])
	 if (Success != 0): 
	 	lLogger.error(" LCP_ANY : Failed Running /usr/sbin/lcp_crtpol2")
		return 0
	 Success=subprocess.call(["/usr/sbin/lcp_writepol","-i","default","-f","./lcp_any.pol","-p","ownerauth"])
         if (Success != 0):
		lLogger.error(" LCP_ANY : Failed Running /usr/sbin/lcp_writepol,default")
		return 0
	 else:
		lLogger.info("Successfully executed LCP_PS_ANY")
		return 1




def disablerecovery():
    #  System call writing value 0x71 to CMOS register at offset 0x70
        os.system("outb 0x70 0x71")

    # Read the value of 0x70 at offset 0x71
        a=subprocess.Popen(["inb","0x71"],stdout=subprocess.PIPE)

    # Removes the new character end of the standard output.
        out=a.stdout.read().rstrip('\n')

    #Checking the last bit of value at offset 0x71. 
        if (int(out) & (0x01) == 0x01):

    # Current bit value is 'one' , its needs to be zero to Disable Recovery.
                lLogger.info("Disabling Recovery.....")

    # Performing 'and' operation with 0x00 to change the lastbit from one to zero.
                DisableValue= (int(out) & 0xFFFFFFFE)
	        Success=subprocess.call(["outb","0x71",DisableValue])
		if (Success !=0):
			lLogger.error("OS command to write to IO address 0x70 failed")
			return 0
        	else:
    # Enters here if the system is already disbaled i.e. the last bit at Address 0x71 is 'zero'
                	lLogger.info("Recovery Success....")
	else:
		lLogger.info("Bit0 of NVRAM 0x71 is '0', so we'll do not need to clear it")
	return 1


###########################lcp1 Function############################  
def lcp1():	
	print "\n"
	print " **********************************LCP1 PO MLE**********************************"
	print "\n"
	Success=lcp_any()
	if (not Success):
		return 0
	else:	
	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list1.lst ./tbootmle.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list1.pol --data ./list1.data ./list1.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f ./list1.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./list1.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP1:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 1 policy written")
			return 1
		else:
			lLogger.info("Failed....")
			return 0


#+----------------------------------------------------------------------------+
			# LCP 2 #

def lcp2():
	print "\n"
	print " **********************************LCP2 PO MLE Mismatch (Negative Test)**********************************"
	print "\n"
	#Measuring the Launch environment i.e.tboot.gz
	lLogger.info( "Running /usr/sbin/lcp_mlehash")
	SCommand="lcp_mlehash -c 'logging=com1' /boot/tboot.gz"
        Command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)	
	if (Command !=0):
		lLogger.error("Failed : Running /usr/sbin/lcp_mlehash")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_hash")
	SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_hash"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00  --minver 0 --out ./tbootmle2.elt ./tboot_hash")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt")
	SCommand="lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt")
		return 0
	#Policy and data files creation
	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list2.pol --data ./list2.data ./list2.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list2.pol --data ./list2.data ./list2.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list2.pol --data ./list2.data ./list2.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list2.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list2.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list2.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list2.data /boot/list.data")
	SCommand="cp ./list2.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list2.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
       # SCommand='sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT="TBOOT>TBOOT LCP"/g' /usr/local/etc/default/grub'
	Command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 2 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 2")	
		return 0

#+----------------------------------------------------------------------------+
				#LCP 3

def lcp3():
	print "\n"
	print " **********************************LCP3 PO PCONF**********************************"
	print "\n"
	lLogger.info("Running cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
	Command=os.system("cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0 ")
	if (Command !=0):
		lLogger.info("Failed :Running cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0")
	SCommand="lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list3.lst ./pconf0.elt")
	SCommand="lcp_crtpollist --create --out ./list3.lst ./pconf0.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list3.lst ./pconf0.elt")
		return 0
	#Policy and data files creation
	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list3.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list3.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list3.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list3.data /boot/list.data")
	SCommand="cp ./list3.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list3.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 3 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 3")	
		return 0
#+----------------------------------------------------------------------------+
			# LCP 4

def lcp4():
	print "\n"
	print " **********************************LCP4 PO PCONF Mismatch (Negative Test)**********************************"
	print "\n"
	lLogger.info( "Running echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
        Command=os.system("echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
	if (Command !=0):
		lLogger.error("Failed : Running echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > bad_pcr")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr")
	SCommand="lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list4.lst ./badconf.elt")
	SCommand="lcp_crtpollist --create --out ./list4.lst ./badpconf.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list4.lst ./badpconf.elt")
		return 0
	#Policy and data files creation
	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list4.pol --data ./list4.data ./list4.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list4.pol --data ./list4.data ./list4.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list4.pol --data ./list4.data ./list4.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list4.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list4.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list4.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list4.data /boot/list.data")
	SCommand="cp ./list4.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list4.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 4 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 4")	
		return 0

#+----------------------------------------------------------------------------+
			# LCP5
def lcp5():
	print "\n"
	print " **********************************LCP5 PO MLE Signed w/ Incorrect Size***********************************"
	print "\n"
	lLogger.info("Running openssl genrsa -out ./privkey2048.pem 2048")
	SCommand="openssl genrsa -out ./privkey2048.pem 2048"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running openssl genrsa -out ./privkey2048.pem 2048")
		return 0
	lLogger.info("Running openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem")
	SCommand="openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem")
		return 0
	#Measuring the Launch environment i.e.tboot.gz
	lLogger.info( "Running /usr/sbin/lcp_mlehash")
	SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
        Command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)	
	if (Command !=0):
		lLogger.error("Failed : Running /usr/sbin/lcp_mlehash")
		return 0
	#MLE element creation
	lLogger.info(" Running llcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle5.elt ./tboot_hash")
	SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle5.elt ./tboot_hash"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle5.elt ./tboot_hash")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list5_sig.lst ./tbootmle5.elt")
	SCommand="lcp_crtpollist --create --out ./list5_sig.lst ./tbootmle5.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt")
		return 0
	lLogger.info("Running lcp_crtpollist --sign --pub ./pubkey2048.pem --priv ./privkey2048.pem --out ./list5_sig.lst")
	SCommand="lcp_crtpollist --sign --pub ./pubkey2048.pem --priv ./privkey2048.pem --out ./list5_sig.lst"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed: Running lcp_crtpollist --sign --pub ./pubkey2048.pem --priv ./privkey2048.pem --out ./list5_sig.lst")
		return 0
	#Policy and data files creation
	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list5.pol --data ./list5.data ./list5_sig.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list5.pol --data ./list5.data ./list5_sig.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list5.pol --data ./list5.data ./list5_sig.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list5.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list5.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list5.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list5.data /boot/list.data")
	SCommand="cp ./list5.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list5.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 5 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 5")	
		return 0



#+----------------------------------------------------------------------------+
			# LCP 6

def lcp6():
	print "\n"
	print " **********************************LCP6 PO MLE Signed w/ Incorrect Size (Negative Test)***********************************"
	print "\n"
	lLogger.info("Running openssl genrsa -out ./privkey1024.pem 1024")
	SCommand="openssl genrsa -out ./privkey1024.pem 1024"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running openssl genrsa -out ./privkey1024.pem 1024")
		return 0
	lLogger.info("Running openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem")
	SCommand="openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem")
		return 0
	#Measuring the Launch environment i.e.tboot.gz
	lLogger.info( "Running /usr/sbin/lcp_mlehash")
	SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
        Command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)	
	if (Command !=0):
		lLogger.error("Failed : Running /usr/sbin/lcp_mlehash")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle6.elt ./tboot_hash")
	SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle6.elt ./tboot_hash"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00  --minver 0 --out ./tbootmle6.elt ./tboot_hash")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt")
	SCommand="lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt")
		return 0
	lLogger.info("Running lcp_crtpollist --sign --pub ./pubkey1024.pem --priv ./privkey1024.pem --out ./list6_sig.lst")
	SCommand="lcp_crtpollist --sign --pub ./pubkey1024.pem --priv ./privkey1024.pem --out ./list6_sig.lst"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed: Running lcp_crtpollist --sign --pub ./pubkey1024.pem --priv ./privkey1024.pem --out ./list6_sig.lst")
		return 0
	#Policy and data files creation

	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list5.pol --data ./list5.data ./list5_sig.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list6.pol --data ./list6.data ./list6_sig.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list6.pol --data ./list6.data ./list6_sig.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list6.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list6.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list6.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list6.data /boot/list.data")
	SCommand="cp ./list6.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list6.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 5 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 5")	
		return 0




#+----------------------------------------------------------------------------+
			#LCP 7
def lcp7():
	print "\n"
	print " **********************************LCP7**********************************"
	print "\n"
	TxtStatus=open("txt-stat.log","w")
	i="txt-stat"
	try:
		sCommand=subprocess.call(_shlex.split(i),stdout=TxtStatus)
	except Exception:
		lLogger.error("Not able to retrieve data from TXT-STAT command")
	else:
		TxtStatFileContents=open("txt-stat.log","r")
		TxtStatLine=TxtStatFileContents.readlines()
		for sLine in TxtStatLine:
			if _re.search("acm_ver",sLine):
				s=_re.findall('\d+',sLine)
				lLogger.info("The Acm version found , its value is %s" %s)
				AcmVersion=s[0]
				HexValueAcmVersion=hex(int(AcmVersion)+1)
				print "%s" %HexValueAcmVersion
		Success=lcp_ps_any()
		if (not Success):
			return 0
		else:	
		#Measuring the Launch environment i.e.tboot.gz 
			lLogger.info(" Running /usr/sbin/lcp_mlehash")
			SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz > ./tboot_hash"
			command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
		#MLE element creation	
			if (command!= 0):
				lLogger.error("LCP7:Failed Running /usr/sbin/lcp_mlehash ")
				return 0
			lLogger.info("Running /usr/sbin/lcp_crtpolelt")
			SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver HexValueAcmVersion --out ./minver.elt ./tboot_hash"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running /usr/sbin/lcp_crtpolel ")
				return 0
		#MLE list creation
			lLogger.info("Running /usr/sbin/lcp_crtpollist")
			SCommand="lcp_crtpollist --create --out ./list7.lst ./minver.elt"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running /usr/sbin/lcp_crtpollist ")
				return 0
		#Policy and data files creation
			lLogger.info(" Running /usr/sbin/lcp_crtpol2")
			SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list7.pol --data ./list7.data ./list7.lst"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running /usr/sbin/lcp_crtpol2 ")
				return 0
		#Write the policy to TPM
			lLogger.info("Running /usr/sbin/lcp_writepol")
			SCommand="lcp_writepol -i owner -f ./list7.pol -p ownerauth"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running /usr/sbin/lcp_writepol ")
				return 0
		#Copy policy data to boot directory
			lLogger.info("Running cp,./list1.data,/boot/list.data")
			SCommand="cp ./list7.data /boot/list.data"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running cp,./list1.data,/boot/list.data ")
				return 0
		#Create a new Grub enty with the LCP policy
			lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
			command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
			if (command!= 0):
				lLogger.error(" LCP7:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
				return 0
			lLogger.info("Running grub-mkconfig")
			SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP7:Failed Running grub-mkconfig")
				return 0	
			lLogger.info("Running disablerecovery()")
			command=disablerecovery()
			if command ==1:
				lLogger.info("Successfully Lcp 7 policy written")
				return 1
			else:
				lLogger.error("Failed....")
				return 0

#+----------------------------------------------------------------------------+
			#LCP 8

def lcp8():
	print "\n"
	print " **********************************LCP8**********************************"
	print "\n"
	TxtStatus=open("txt-stat.log","w")
	i="txt-stat"
	try:
		sCommand=subprocess.call(_shlex.split(i),stdout=TxtStatus)
	except Exception:
		lLogger.error("Not able to retrieve data from TXT-STAT command")
	else:
		TxtStatFileContents=open("txt-stat.log","r")
		TxtStatLine=TxtStatFileContents.readlines()
		for sLine in TxtStatLine:
			if _re.search("acm_ver",sLine):
				s=_re.findall('\d+',sLine)
				lLogger.info("The Acm version found , its value is %s" %s)
				AcmVersion=s[0]
				HexValueAcmVersion=hex(int(AcmVersion)+1)
				print "%s" %HexValueAcmVersion
		Success=lcp_ps_any()
		if (not Success):
			return 0
		else:	
		#Measuring the Launch environment i.e.tboot.gz 
			lLogger.info(" Running /usr/sbin/lcp_mlehash")
			SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz > ./tboot_hash"
			command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
		#MLE element creation	
			if (command!= 0):
				lLogger.error("LCP8:Failed Running /usr/sbin/lcp_mlehash ")
				return 0
			lLogger.info("Running /usr/sbin/lcp_crtpolelt")
			SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver HexValueAcmVersion --out ./minver.elt ./tboot_hash"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running /usr/sbin/lcp_crtpolel ")
				return 0
		#MLE list creation
			lLogger.info("Running /usr/sbin/lcp_crtpollist")
			SCommand="lcp_crtpollist --create --out ./list8.lst ./minver.elt"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running /usr/sbin/lcp_crtpollist ")
				return 0
		#Policy and data files creation
			lLogger.info(" Running /usr/sbin/lcp_crtpol2")
			SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list8.pol --data ./list8.data ./list8.lst"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running /usr/sbin/lcp_crtpol2 ")
				return 0
		#Write the policy to TPM
			lLogger.info("Running /usr/sbin/lcp_writepol")
			SCommand="lcp_writepol -i owner -f ./list8.pol -p ownerauth"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running /usr/sbin/lcp_writepol ")
				return 0
		#Copy policy data to boot directory
			lLogger.info("Running cp,./list1.data,/boot/list.data")
			SCommand="cp ./list8.data /boot/list.data"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running cp,./list1.data,/boot/list.data ")
				return 0
		#Create a new Grub enty with the LCP policy
			lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
			command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
			if (command!= 0):
				lLogger.error(" LCP8:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
				return 0
			lLogger.info("Running grub-mkconfig")
			SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP8:Failed Running grub-mkconfig")
				return 0	
			lLogger.info("Running disablerecovery()")
			command=disablerecovery()
			if command ==1:
				lLogger.info("Successfully Lcp 8 policy written")
				return 1
			else:
				lLogger.error("Failed....")
				return 0

#+----------------------------------------------------------------------------+
				#LCP 9
def lcp9():	
	print "\n"
	print " **********************************LCP1 PO MLE**********************************"
	print "\n"
	Success=lcp_any()
	if (not Success):
		return 0
	else:	
	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle9.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list9.lst ./tbootmle9.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list9.pol --data ./list9.data ./list9.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f ./list9.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./list9.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP1:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP9:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 9 policy written")
			return 1
		else:
			lLogger.error("Failed....")
			return 0		

#+------------------------------------------------------------------------------------------+
			# LCP 10

def lcp10():	
	print "\n"
	print " **********************************LCP1 PO MLE**********************************"
	print "\n"
	Success=lcp_ps_any()
	if (not Success):
		return 0
	else:	
	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP10:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle10.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP10:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list10.lst ./tbootmle10.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP10:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x00 --pol ./list10.pol --data ./list10.data ./list10.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP10:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f ./list10.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP10:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./list10.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP10:Failed Running cp,./list1.data,/boot/list.data ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP10:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 10 policy written")
			return 1
		else:
			lLogger.info("Failed....")
			return 0


#+---------------------------------------------------------------------------------------------+
				#LCP 15
def lcp15():	
	print "\n"
	print " **********************************LCP15 PO MLE**********************************"
	print "\n"
	#Create a file with modified PCR00 value
	lLogger.info("Running the creation of bad_pcr i.e. modified PCR00")
	SCommand="echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF"
	bad_pcr=("./bad_pcr","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP15:Failed Creating bad_pcr ")
		return 0
	#MLE element creation	
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list15.lst ./badpconf.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list15.pol --data ./list15.data ./list15.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPMi
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i default -f list15.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	# Create a file with PCR00 values
		lLogger.info("Creating a file with Current PCR00 values")
		command=_os.system("cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
		if (command!= 0):
			lLogger.error("LCP15:Failed to create PCR00 file ")
			return 0
	#MLE element creation	
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type pconf --ctrl 0x01 --out ./1pconf0.elt ./pcr0"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./1list15.lst ./1pconf0.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./1list15.pol --data ./1list15.data ./1list15.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPMi
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f 1list15.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./1list15.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP1:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP15:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 1 policy written")
			return 1
		else:
			lLogger.info("Failed....")
			return 0

#+----------------------------------------------------------------------------------------------+
			#LCP 16
def lcp16():	
	print "\n"
	print " **********************************LCP16 PO MLE**********************************"
	print "\n"
	# Create a file with PCR00 values
	lLogger.info("Creating a file with Current PCR00 values")
	command=_os.system("cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
	if (command!= 0):
		lLogger.error("LCP15:Failed to create PCR00 file ")
		return 0
	#Create a file with modified PCR01 value
	lLogger.info("Running the creation of pcrA i.e. modified PCR01")
	SCommand="echo PCR-01: AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA AA"
	bad_pcr=("./pcrA","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-A ")
		return 0
	#Create a file with modified PCR02 value
	lLogger.info("Running the creation of pcrB i.e. modified PCR02")
	SCommand="echo PCR-02: BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB BB"
	bad_pcr=("./pcrB","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-B ")
		return 0
	#Create a file with modified PCR03 value
	lLogger.info("Running the creation of pcrC i.e. modified PCR03")
	SCommand="echo PCR-03: CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC"
	bad_pcr=("./pcrC","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-C ")
		return 0
	#Create a file with modified PCR04 value
	lLogger.info("Running the creation of pcrD i.e. modified PCR04")
	SCommand="echo PCR-04: DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD DD"
	bad_pcr=("./pcrD","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-D ")
		return 0
	#Create a file with modified PCR05 value
	lLogger.info("Running the creation of pcrE i.e. modified PCR05")
	SCommand="echo PCR-05: EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE EE"
	bad_pcr=("./pcrE","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-E ")
		return 0
	#Create a file with modified PCR06 value
	lLogger.info("Running the creation of pcrF i.e. modified PCR06")
	SCommand="echo PCR-06: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF" 
	bad_pcr=("./pcrF","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-F ")
		return 0
	#Create a file with modified PCR07 value
	lLogger.info("Running the creation of pcrA1 i.e. modified PCR07")
	SCommand="echo PCR-07: A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1 A1"
	bad_pcr=("./pcrA1","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-A1 ")
		return 0
	#Create a file with modified PCR08 value
	lLogger.info("Running the creation of pcrB2 i.e. modified PCR08")
	SCommand="echo PCR-08: B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1 B1" 
	bad_pcr=("./pcrB1","w")
	command=subprocess.call(_shlex.split(SCommand),stdout=bad_pcr)
	if (command!= 0):
		lLogger.error("LCP16:Failed Creating PCR-B1 ")
		return 0
	#MLE element creation	
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type pconf --out ./pconf16.elt ./pcr0 ./pcrA ./pcrB ./pcrC ./pcrD ./pcrE ./pcrF ./pcrA1 ./pcrB1"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list16.lst ./pconf16.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list16.pol --data ./list16.data ./list16.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
	#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f list16.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./list16.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP1:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 16 policy written")
			return 1
		else:
			lLogger.info("Failed....")
			return 0

#+-------------------------------------------------------------------------------------------+
			# LCP 18
def lcp18():	
	print "\n"
	print " **********************************LCP1 PO MLE**********************************"
	print "\n"
	Success=lcp_any()
	if (not Success):
		return 0
	else:	
	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0xFF --out ./tbootmle.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list1.lst ./tbootmle.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0

	#Measuring the Launch environment i.e.tboot.gz
	lLogger.info( "Running /usr/sbin/lcp_mlehash")
	SCommand="lcp_mlehash -c 'logging=com1' /boot/tboot.gz"
        Command=subprocess.call(_shlex.split(SCommand),stdout=tboot_bad_hash)	
	if (Command !=0):
		lLogger.error("Failed : Running /usr/sbin/lcp_mlehash")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_hash")
	SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_bad_hash"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00  --minver 0 --out ./tbootmle2.elt ./tboot_hash")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt")
	SCommand="lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt")
		return 0

	lLogger.info( "Running echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
        Command=os.system("echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
	if (Command !=0):
		lLogger.error("Failed : Running echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > bad_pcr")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr")
	SCommand="lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type pconf --out ./badpconf.elt ./bad_pcr")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list4.lst ./badconf.elt")
	SCommand="lcp_crtpollist --create --out ./list4.lst ./badpconf.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list4.lst ./badpconf.elt")
		return 0

	lLogger.info("Running openssl genrsa -out ./privkey1024.pem 1024")
	SCommand="openssl genrsa -out ./privkey1024.pem 1024"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running openssl genrsa -out ./privkey1024.pem 1024")
		return 0
	lLogger.info("Running openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem")
	SCommand="openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running openssl rsa -pubout -in ./privkey1024.pem -out ./pubkey1024.pem")
		return 0
	#Measuring the Launch environment i.e.tboot.gz
	lLogger.info( "Running /usr/sbin/lcp_mlehash")
	SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
        Command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)	
	if (Command !=0):
		lLogger.error("Failed : Running /usr/sbin/lcp_mlehash")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle6.elt ./tboot_hash")
	SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle6.elt ./tboot_hash"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00  --minver 0 --out ./tbootmle6.elt ./tboot_hash")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt")
	SCommand="lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list6_sig.lst ./tbootmle6.elt")
		return 0
	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga' /boot/tboot-262.gz> ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./badminver.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list8.lst ./badminver.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP1:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0


	#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga' /boot/tboot-262.gz> ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
	#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list10.lst ./tbootmle.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle18.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
	#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list18.lst ./tbootmle18.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
	#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol list18.pol --data list18.data ./list1.lst ./list2.lst ./list6_sig.lst ./list8.lst ./list10.lst ./list18.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0


	#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f list18.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp list18.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running /usr/sbin/lcp_writepol ")
			return 0
	#Create a new Grub enty with the LCP policy
		lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
		command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
		if (command!= 0):
			lLogger.error(" LCP18:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
			return 0
		lLogger.info("Running grub-mkconfig")
		SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP18:Failed Running grub-mkconfig")
			return 0	
		lLogger.info("Running disablerecovery()")
		command=disablerecovery()
		if command ==1:
			lLogger.info("Successfully Lcp 18 policy written")
			return 1
		else:
			lLogger.info("Failed....")
			return 0


#+----------------------------------------------------------------------------------------------+
		 #LCP 19


def lcp19():
	print "\n"
	print " **********************************LCP19 PO PCONF**********************************"
	print "\n"
	lLogger.info("Running cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
	Command=os.system("cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0 ")
	if (Command !=0):
		lLogger.info("Failed :Running cat `find /sys/devices/ -name pcrs` | grep PCR-00 > ./pcr0")
		return 0
	#MLE element creation
	lLogger.info(" Running lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0")
	SCommand="lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed: Running lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0")
		return 0
	#MLE list creation
	lLogger.info("Running lcp_crtpollist --create --out ./list3.lst ./pconf0.elt")
	SCommand="lcp_crtpollist --create --out ./list3.lst ./pconf0.elt"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed :Running lcp_crtpollist --create --out ./list3.lst ./pconf0.elt")
		return 0
	#Policy and data files creation
	lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst")
	SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst"
	Command= subprocess.call(_shlex.split(SCommand))
	if (Command !=0):
		lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst")
		return 0
	#Write the policy to TPM
	lLogger.info("Running lcp_writepol -i owner -f ./list3.pol -p ownerauth")
	SCommand="lcp_writepol -i owner -f ./list3.pol -p ownerauth"
        Command=subprocess.call(_shlex.split(SCommand))
        if (Command != 0):
                lLogger.error("Failed:Running lcp_writepol -i owner -f ./list3.pol -p ownerauth")
		return 0
        #Copy policy data to boot directory
	lLogger.info("Running cp ./list3.data /boot/list.data")
	SCommand="cp /boot/list3_9.data /boot/list.data"
	Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running cp ./list3.data /boot/list.data")
		return 0
	#Create a new Grub enty with the LCP policy
	lLogger.info("Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running sed -i 's/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g' /usr/local/etc/default/grub")
		return 0
	lLogger.info("Running grub-mkconfig -o /boot/grub/grub.cfg")
	SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
        Command=subprocess.call(_shlex.split(SCommand))
	if (Command != 0):
		lLogger.error("Failed :Running grub-mkconfig -o /boot/grub/grub.cfg")
         	return 0       
	Func_Call=disablerecovery()
        if Func_Call ==1:
		lLogger.info("Successfully LCP 19 policy written")
		return 1
	else:
		lLogger.error("Failed Writting LCP 19")	
		return 0

#+----------------------------------------------------------------------------+
			#LCP 20
def lcp20():
	print "\n"
	print " **********************************LCP20 ***********************************"
	print "\n"
	Success=releasePO()
	if (not Success):
		return 0
	else:
		lLogger.info("Running openssl genrsa -out ./privkey2048.pem 2048")
		SCommand="openssl genrsa -out ./privkey2048.pem 2048"
		Command=subprocess.call(_shlex.split(SCommand))
		if (Command !=0):
			lLogger.error("Failed: Running openssl genrsa -out ./privkey2048.pem 2048")
			return 0
		lLogger.info("Running openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem")
		SCommand="openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem"
		Command=subprocess.call(_shlex.split(SCommand))
		if (Command !=0):
			lLogger.error("Failed :Running openssl rsa -pubout -in ./privkey2048.pem -out ./pubkey2048.pem")
			return 0
	#MLE list creation
		lLogger.info("Running lcp_crtpollist --create --out ./list22_sig.lst")
		SCommand="lcp_crtpollist --create --out list22_sig.lst"
        	Command=subprocess.call(_shlex.split(SCommand))
		if (Command !=0):
			lLogger.error("Failed :Running lcp_crtpollist --create --out ./list22_sig.lst ")
			return 0
		lLogger.info("Running lcp_crtpollist --sign --pub pubkey2048.pem --priv privkey2048.pem --out list22_sig.lst")
		SCommand="lcp_crtpollist --sign --pub pubkey2048.pem --priv privkey2048.pem --out list22_sig.lst"
		Command=subprocess.call(_shlex.split(SCommand))
		if (Command != 0):
			lLogger.error("Failed: Running lcp_crtpollist --sign --pub ./pubkey2048.pem --priv ./privkey2048.pem --out ./list22_sig.lst")
			return 0
	#Policy and data files creation
		lLogger.info("Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol list22.pol --data list22.data list22_sig.lst")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol list22.pol --data list22.data list22_sig.lst"
		Command= subprocess.call(_shlex.split(SCommand))
		if (Command !=0):
			lLogger.error("Failed:Running lcp_crtpol2 --create --type list --ctrl 0x02 --pol list22.pol --data list22.data list22_sig.lst")
			return 0
	#Write the policy to TPM
		lLogger.info("Running lcp_writepol -i default -f list22.pol -p ownerauth")
		SCommand="lcp_writepol -i default -f list22.pol -p ownerauth"
        	Command=subprocess.call(_shlex.split(SCommand))
        	if (Command != 0):
                	lLogger.error("Failed:Running lcp_writepol -i default -f list22.pol -p ownerauth")
			return 0
		else:
			return 1

#+----------------------------------------------------------------------------+
			#LCP 21

def lcp21():
	print "\n"
	print " **********************************LCP21**********************************"
	print "\n"
	TxtStatus=open("txt-stat.log","w")
	i="txt-stat"
	try:
		sCommand=subprocess.call(_shlex.split(i),stdout=TxtStatus)
	except Exception:
		lLogger.error("Not able to retrieve data from TXT-STAT command")
	else:
		TxtStatFileContents=open("txt-stat.log","r")
		TxtStatLine=TxtStatFileContents.readlines()
		for sLine in TxtStatLine:
			if _re.search("acm_ver",sLine):
				s=_re.findall('\d+',sLine)
				lLogger.info("The Acm version found , its value is %s" %s)
				AcmVersion=s[0]
				HexValueAcmVersion=hex(int(AcmVersion))
				#print "%s" %HexValueAcmVersion
		#Measuring the Launch environment i.e.tboot.gz 
		lLogger.info(" Running /usr/sbin/lcp_mlehash")
		SCommand="lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz > ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
		#MLE element creation	
		if (command!= 0):
			lLogger.error("LCP21:Failed Running /usr/sbin/lcp_mlehash ")
			return 0
		lLogger.info("Running /usr/sbin/lcp_crtpolelt")
		SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver HexValueAcmVersion --out ./minver.elt ./tboot_hash"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpolel ")
			return 0
		#MLE list creation
		lLogger.info("Running /usr/sbin/lcp_crtpollist")
		SCommand="lcp_crtpollist --create --out ./list7.lst ./minver.elt"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpollist ")
			return 0
		#Policy and data files creation
		lLogger.info(" Running /usr/sbin/lcp_crtpol2")
		SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list7.pol --data ./list7.data ./list7.lst"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpol2 ")
			return 0
		#Write the policy to TPM
		lLogger.info("Running /usr/sbin/lcp_writepol")
		SCommand="lcp_writepol -i owner -f ./list7.pol -p ownerauth"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP21:Failed Running /usr/sbin/lcp_writepol ")
			return 0
		#Copy policy data to boot directory
		lLogger.info("Running cp,./list1.data,/boot/list.data")
		SCommand="cp ./list7.data /boot/list.data"
		command=subprocess.call(_shlex.split(SCommand))
		if (command!= 0):
			lLogger.error("LCP21:Failed Running cp,./list1.data,/boot/list.data ")
			return 0
		try:
			sCommand=subprocess.call(_shlex.split(i),stdout=TxtStatus)
		except Exception:
			lLogger.error("Not able to retrieve data from TXT-STAT command")
		else:
			TxtStatFileContents=open("txt-stat.log","r")
			TxtStatLine=TxtStatFileContents.readlines()
			for sLine in TxtStatLine:
				if _re.search("acm_ver",sLine):
					s=_re.findall('\d+',sLine)
					AcmVersion=s[0]
					HexValueAcmMaxVersion=hex(int(AcmVersion)+1)
				#	print "%s" %HexValueAcmMaxVersion
		#MLE element creation	
			lLogger.info("Running /usr/sbin/lcp_crtpolelt")
			SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver HexValueAcmMaxVersion --out ./maxver.elt ./tboot_hash"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpolel ")
				return 0
		#MLE list creation
			lLogger.info("Running /usr/sbin/lcp_crtpollist")
			SCommand="lcp_crtpollist --create --out ./list21.lst ./maxver.elt"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpollist ")
				return 0
		#Policy and data files creation
			lLogger.info(" Running /usr/sbin/lcp_crtpol2")
			SCommand="lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list21.pol --data ./list21.data ./list21.lst"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP21:Failed Running /usr/sbin/lcp_crtpol2 ")
				return 0
		#Write the policy to TPM
			lLogger.info("Running /usr/sbin/lcp_writepol")
			SCommand="lcp_writepol -i owner -f ./list21.pol -p ownerauth"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP21:Failed Running /usr/sbin/lcp_writepol ")
				return 0

		#Create a new Grub enty with the LCP policy
			lLogger.info("Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT")
			command=subprocess.call(["sed","-i","s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT LCP'/g","/usr/local/etc/default/grub"])
			if (command!= 0):
				lLogger.error(" LCP8:Failed Running sed,-i,s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOTl ")
				return 0
			lLogger.info("Running grub-mkconfig")
			SCommand="grub-mkconfig -o /boot/grub/grub.cfg"
			command=subprocess.call(_shlex.split(SCommand))
			if (command!= 0):
				lLogger.error("LCP21:Failed Running grub-mkconfig")
				return 0	
			lLogger.info("Running disablerecovery()")
			command=disablerecovery()
			if command ==1:
				lLogger.info("Successfully Lcp 21 policy written")
				return 1
			else:
				lLogger.error("Failed....")
				return 0


def lcp25():	
	print "\n"
	print " **********************************LCP25 NPW PO Override PW PS **********************************"
	print "\n"
	#Policy and data files creation
	lLogger.info("LCP_PS Running /usr/sbin/lcp_crtpol2")
	SCommand="lcp_crtpol2 --create --type any --ctrl 0x00 --pol ./lcp_any.pol"
	command=subprocess.call(_shlex.split(SCommand))
	if (command!= 0):
		lLogger.error("LCP_PS_25:Failed Running /usr/sbin/lcp_crtpol2 ")
		return 0
	#Write the policy to TPM
	lLogger.info("LCP_PS Running /usr/sbin/lcp_writepol")
	SCommand="lcp_writepol -i default -f ./lcp_any.pol -p ownerauth"
	command=subprocess.call(_shlex.split(SCommand))
	if (command!= 0):
		lLogger.error("LCP_25_PS:Failed Running /usr/sbin/lcp_writepol ")
		return 0

	#Policy and data files creation
	lLogger.info("LCP_PO Running /usr/sbin/lcp_crtpol2")
	SCommand="lcp_crtpol2 --create --type any --ctrl 0x02 --pol ./lcp_any.pol"
	command=subprocess.call(_shlex.split(SCommand))
	if (command!= 0):
		lLogger.error("LCP_PO_25:Failed Running /usr/sbin/lcp_crtpol2 ")
		return 0
	#Write the policy to TPM
	lLogger.info("LCP_PO Running /usr/sbin/lcp_writepol")
	SCommand="lcp_writepol -i owner -f ./lcp_any.pol -p ownerauth"
	command=subprocess.call(_shlex.split(SCommand))
	if (command!= 0):
		lLogger.error("LCP_PO_25:Failed Running /usr/sbin/lcp_writepol ")
		return 0
	else:
		lLogger.info("Successfully Lcp 25 policy written")
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
    bErrorsOccurred         = False # used to short-circuit certain steps if errors found

    #  Startup tasks - get the logger configured
    _ValToolsUtilities.printStartupBanner(lLogger, nOutputWidth, 
                                          sScriptName, __version__)

    #  Get command line options, if any
    oCmdlineOptions = parseCommandLine()

   
    if (oCmdlineOptions.Policy == "1"):
		lLogger.info("Found LCP 1...Executing....")
		bErrorsOccurred = not(lcp1())
    elif (oCmdlineOptions.Policy == "2"):
		lLogger.info("Found LCP 2...EXecuting....")
		bErrorsOccurred =not(lcp2())
    elif (oCmdlineOptions.Policy == "3"):
		lLogger.info("Found LCP 3...Executing....")
		bErrorsOccured =not(lcp3())
    elif (oCmdlineOptions.Policy == "4"):
		lLogger.info("Found LCP 4...Executing....")
		bErrorsOccured=not(lcp4())
    elif (oCmdlineOptions.Policy =="5"):
		lLogger.info("Found LCP 5...Executing....")
		bErrorsOccured=not(lcp5())
    elif (oCmdlineOptions.Policy =="6"):
		lLogger.info("Found LCP 6...Executing....")
		bErrorsOccured=not(lcp6())
    elif (oCmdlineOptions.Policy =="7"):
		lLogger.info("Found LCP 7...Executing....")
		bErrorsOccured=not(lcp7())
    elif (oCmdlineOptions.Policy =="8"):
		lLogger.info("Found LCP 8...Executing....")
		bErrorsOccured=not(lcp8())
    elif (oCmdlineOptions.Policy =="9"):
		lLogger.info("Found LCP 9...Executing....")
		bErrorsOccured=not(lcp9())
    elif (oCmdlineOptions.Policy =="10"):
		lLogger.info("Found LCP 10...Executing....")
		bErrorsOccured=not(lcp10())
    elif (oCmdlineOptions.Policy =="15"):
		lLogger.info("Found LCP 11...Executing....")
		bErrorsOccured=not(lcp15())
    elif (oCmdlineOptions.Policy =="16"):
		lLogger.info("Found LCP 16...Executing....")
		bErrorsOccured=not(lcp16())
    elif (oCmdlineOptions.Policy =="18"):
		lLogger.info("Found LCP 18...Executing....")
		bErrorsOccured=not(lcp18())

    elif (oCmdlineOptions.Policy == "19"):
		lLogger.info("Found LCP 19...EXecuting....")
		bErrorsOccurred =not(lcp19())
    elif (oCmdlineOptions.Policy == "21"):
		lLogger.info("Found LCP 21...Executing....")
		bErrorsOccured =not(lcp21())
    elif (oCmdlineOptions.Policy == "20"):
		lLogger.info("Found LCP 20...Executing....")
		bErrorsOccured =not(lcp20())
    elif (oCmdlineOptions.Policy == "25"):
		lLogger.info("Found LCP 25...Executing....")
		bErrorsOccured =not(lcp25())
    else:
		lLogger.info("--policy option set to '%s'" % oCmdlineOptions.Policy)
		lLogger.info("    Right now I only know about '1'.")
		bErrorsOccurred = True

    #  Return boolean indicating whether we were successful or not
    _ValToolsUtilities.printFinishingBanner(lLogger, bErrorsOccurred, nOutputWidth,
                                               sScriptName, __version__)
    return (not bErrorsOccurred)
    







####################################################################################

if __name__ == '__main__':
    if main():
        lLogger.info("Exiting with zero status...")
        _sys.exit(0)
    else:
        lLogger.info("Exiting with non-zero status...")
        _sys.exit(1)


