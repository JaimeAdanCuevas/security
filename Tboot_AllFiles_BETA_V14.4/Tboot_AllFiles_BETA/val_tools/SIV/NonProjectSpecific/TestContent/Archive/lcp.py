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
#| $Id: lcp.py 101 2015-01-23 02:28:06Z amr\egross $
#| $Date: 2015-01-22 18:28:06 -0800 (Thu, 22 Jan 2015) $
#| $Author: amr\egross $
#| $Revision: 101 $
#+----------------------------------------------------------------------------+
#| TODO:
#|      *  All LCPs > LCP2 need to be redone.
#|      *  LCP1 needs to be cleaned up and modularized to make it a template
#|         for the rest of the LCPs
#|      *  Remove PSANY from all LCP flows
#+----------------------------------------------------------------------------+

"""
    Script implements LCP 1 policy
"""

# Standard libary imports
import os      as _os
import sys     as _sys
import re      as _re
import logging as _logging
from optparse import OptionParser
import subprocess
import shlex as _shlex
## Global Variables/Constants
bDEBUG                  = 0
nOutputWidth            = 80
__version__             = "$Rev: 101 $".replace("$Rev:","").replace("$","").strip()
sScriptName             = _re.split("\.", _os.path.basename(__file__))[0]
sLogfileName            = '%s_pid%d.log' % (sScriptName, _os.getpid())
tboot_hash=open("./tboot_hash","w")
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
                      type="choice", choices=["1", "2", "3","4","5"], default="2",
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
    lLogger.info( "\n")
    lLogger.info( " **********************************LcpAny**********************************")
    lLogger.info( "\n")


    #   Run lcp_crtpol2
    #   TODO: Need better comment here and better info output below
    sDescription = "[what does lcp_crtpol2 do?]"
    sCommand     = "/usr/sbin/lcp_crtpol2 --create --type any --ctrl 0x02 -pol ./lcp_any.pol"
    bSuccess     = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
    if (not bSuccess):
        return 0


    #   Run lcp_writepol
    #   TODO: Need better comment here and better info output below
    sDescription = "[what does lcp_writepol do?]"
    sCommand     = "/usr/sbin/lcp_writepol -i owner -f ./lcp_any.pol -p ownerauth"
    bSuccess     = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
    if (not bSuccess):
        return 0


    #   Run lcp_writepol
    #   TODO: Need better comment here and better info output below
    sDescription = "[what does lcp_writepol do?]"
    sCommand     = "/usr/sbin/lcp_writepol -i default -f ./lcp_any.pol -p ownerauth"
    bSuccess     = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
    if (not bSuccess):
        return 0


    #   Modify GRUB config file to select TBOOT by default
    sDescription = "change default grub selection to 'TBOOT>TBOOT'"
    sCommand     = "sed -i s/GRUB_DEFAULT=.*/GRUB_DEFAULT='TBOOT>TBOOT'/g /usr/local/etc/default/grub"
    bSuccess     = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
    if (not bSuccess):
        return 0



    #   Run grub-mkconfig
    #   TODO: Need better comment here and better info output below
    sDescription = "[what does grub-mkconfig do?]"
    sCommand     = "sudo /usr/local/sbin/grub-mkconfig -o /boot/grub/grub.cfg"
    bSuccess     = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
    if (not bSuccess):
        return 0

    #   If we make it this far, we're DONE!
    return 1



def disablerecovery():
    #  System call writing value 0x71 to CMOS register at offset 0x70
    _os.system("outb 0x70 0x71")

    # Read the value of 0x70 at offset 0x71
    a=subprocess.Popen(["inb","0x71"],stdout=subprocess.PIPE)

    # Removes the new character end of the standard output.
    out=a.stdout.read().rstrip('\n')

    #Checking the last bit of value at offset 0x71. 
    if (int(out) & (0x01) == 0x01):

        # Current bit value is 'one' , its needs to be zero to Disable Recovery.
        lLogger.info("Disabling Recovery.....")

        # Performing 'and' operation with 0xFE to change the lastbit from one to zero.
        nDisableValue= (int(out) & 0xFFFFFFFE)
        Success=subprocess.call(["outb","0x71",("0x%x" % nDisableValue)])
        if (Success !=0):
            lLogger.error("OS command to write to IO address 0x71 failed")
            return 0
        else:
            # Enters here if the system is already disbaled i.e. the last bit at Address 0x71 is 'zero'
            lLogger.info("Recovery Success....")
    else:
        lLogger.info("Bit0 of NVRAM 0x71 is '0', so we'll do not need to clear it")
    return 1


###########################lcp1 Function############################  
def lcp1():
    lLogger.info( "\n")
    lLogger.info( " **********************************LCP1 PO MLE**********************************")
    lLogger.info( "\n")
    Success=lcp_any()
    if (not Success):
        return 0
    else:
        lLogger.info( "\n")
        lLogger.info( " *****************************LCP1 Specific Commands****************************")
        lLogger.info( "\n")
        #Measuring the Launch environment i.e.tboot.gz
        lLogger.info("Running /usr/sbin/lcp_mlehash")
        SCommand="/usr/sbin/lcp_mlehash -c 'logging=serial,vga,memory' /boot/tboot.gz"
        command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_mlehash")
            return 0
        #MLE element creation
        lLogger.info("Running /usr/sbin/lcp_crtpolelt")
        SCommand="/usr/sbin/lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle.elt ./tboot_hash"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpolelt")
            return 0
        #MLE list creation
        lLogger.info("Running /usr/sbin/lcp_crtpollist")
        SCommand="/usr/sbin/lcp_crtpollist --create --out ./list1.lst ./tbootmle.elt"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpollist")
            return 0
        #Policy and data files creation
        lLogger.info("Running /usr/sbin/lcp_crtpol2")
        SCommand="/usr/sbin/lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list1.pol --data ./list1.data ./list1.lst"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpol2")
            return 0
        #Write the policy to TPM
        lLogger.info("Running /usr/sbin/lcp_writepol")
        SCommand="/usr/sbin/lcp_writepol -i owner -f ./list1.pol -p ownerauth"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_writepol")
            return 0
        #Copy policy data to boot directory
        lLogger.info("Running cp ./list1.data /boot/list.data")
        SCommand="cp ./list1.data /boot/list.data"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running cp")
            return 0
        #Create a new Grub enty with the LCP policy
        lLogger.info("Running sed")
        SCommand = 'sed -i \'s/GRUB_DEFAULT=.*/GRUB_DEFAULT="TBOOT>TBOOT LCP"/g\' /usr/local/etc/default/grub'
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running sed")
            return 0




        #   Run grub-mkconfig
        #   TODO: Need better comment here and better info output below
        sDescription    = "[what does grub-mkconfig do?]"
        sCommand        = "sudo /usr/local/sbin/grub-mkconfig -o /boot/grub/grub.cfg"
        bSuccess        = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
        if (not bSuccess):
            return 0

        lLogger.info("Running disablerecovery()")
        command=disablerecovery()
        if command ==1:
            lLogger.info("Successfully Lcp 1 policy written")
            return 1
        else:
            lLogger.error("Failed Writing LCP 1")	
            return 0


#+----------------------------------------------------------------------------+
            # LCP 2 #

def lcp2():
    lLogger.info( "\n")
    lLogger.info( " **********************************LCP2 PO MLE Mismatch (Negative Test)**********************************")
    lLogger.info( "\n")
    Success=lcp_any()
    if (not Success):
        return 0
    else:
        lLogger.info( "\n")
        lLogger.info( " *****************************LCP2 Specific Commands****************************")
        lLogger.info( "\n")
        #Measuring the Launch environment i.e.tboot.gz
        lLogger.info("Running /usr/sbin/lcp_mlehash")
        SCommand="lcp_mlehash -c 'logging=com1' /boot/tboot.gz"
        command=subprocess.call(_shlex.split(SCommand),stdout=tboot_hash)
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_mlehash")
            return 0
        #MLE element creation
        lLogger.info("Running /usr/sbin/lcp_crtpolelt")
        SCommand="/usr/sbin/lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_hash"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpolelt")
            return 0
        #MLE list creation
        lLogger.info("Running /usr/sbin/lcp_crtpollist")
        SCommand="/usr/sbin/lcp_crtpollist --create --out ./list2.lst ./tbootmle2.elt"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpollist")
            return 0
        #Policy and data files creation
        lLogger.info("Running /usr/sbin/lcp_crtpol2")
        SCommand="/usr/sbin/lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list2.pol --data ./list2.data ./list2.lst"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpol2")
            return 0
        #Write the policy to TPM
        lLogger.info("Running /usr/sbin/lcp_writepol")
        SCommand="/usr/sbin/lcp_writepol -i owner -f ./list2.pol -p ownerauth"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_writepol")
            return 0
        #Copy policy data to boot directory
        lLogger.info("Running cp ./list2.data /boot/list.data")
        SCommand="cp ./list2.data /boot/list.data"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running cp")
            return 0
        #Create a new Grub enty with the LCP policy
        lLogger.info("Running sed")
        SCommand = 'sed -i \'s/GRUB_DEFAULT=.*/GRUB_DEFAULT="TBOOT>TBOOT LCP"/g\' /usr/local/etc/default/grub'
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running sed")
            return 0




        #   Run grub-mkconfig
        #   TODO: Need better comment here and better info output below
        sDescription    = "[what does grub-mkconfig do?]"
        sCommand        = "sudo /usr/local/sbin/grub-mkconfig -o /boot/grub/grub.cfg"
        bSuccess        = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
        if (not bSuccess):
            return 0

        lLogger.info("Running disablerecovery()")
        command=disablerecovery()
        if command ==1:
            lLogger.info("Successfully Lcp 1 policy written")
            return 1
        else:
            lLogger.error("Failed Writing LCP 2")	
            return 0


#+----------------------------------------------------------------------------+
                #LCP 3

def lcp3():
    lLogger.info( "\n")
    lLogger.info( " **********************************LCP3 PO PCONF**********************************")
    lLogger.info( "\n")
    Success=lcp_any()
    if (not Success):
        return 0
    else:
        lLogger.info( "\n")
        lLogger.info( " *****************************LCP3 Specific Commands****************************")
        lLogger.info( "\n")
        #Getting Current Value of PCR00
        lLogger.info("Running cat")
        SCommand="cat `find /sys/devices/ -name pcrs` | grep PCR-00"
        command=subprocess.call(_shlex.split(SCommand),stdout=pcr0)
        if (command != 0):
            lLogger.error("Failed: Running cat")
            return 0
        #MLE element creation
        lLogger.info("Running /usr/sbin/lcp_crtpolelt")
        SCommand="/usr/sbin/lcp_crtpolelt --create --type pconf --out ./pconf0.elt ./pcr0"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpolelt")
            return 0
        #MLE list creation
        lLogger.info("Running /usr/sbin/lcp_crtpollist")
        SCommand="/usr/sbin/lcp_crtpollist --create --out ./list3.lst ./pconf0.elt"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpollist")
            return 0
        #Policy and data files creation
        lLogger.info("Running /usr/sbin/lcp_crtpol2")
        SCommand="/usr/sbin/lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_crtpol2 --create --type list --ctrl 0x02 --pol ./list3.pol --data ./list3.data ./list3.lst")
            return 0
        #Write the policy to TPM
        lLogger.info("Running /usr/sbin/lcp_writepol")
        SCommand="/usr/sbin/lcp_writepol -i owner -f ./list3.pol -p ownerauth"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running /usr/sbin/lcp_writepol")
            return 0
        #Copy policy data to boot directory
        lLogger.info("Running cp ./list3.data /boot/list.data")
        SCommand="cp ./list3.data /boot/list.data"
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running cp")
            return 0
        #Create a new Grub enty with the LCP policy
        lLogger.info("Running sed")
        SCommand = 'sed -i \'s/GRUB_DEFAULT=.*/GRUB_DEFAULT="TBOOT>TBOOT LCP"/g\' /usr/local/etc/default/grub'
        command=subprocess.call(_shlex.split(SCommand))
        if (command != 0):
            lLogger.error("Failed: Running sed")
            return 0




        #   Run grub-mkconfig
        #   TODO: Need better comment here and better info output below
        sDescription    = "[what does grub-mkconfig do?]"
        sCommand        = "sudo /usr/local/sbin/grub-mkconfig -o /boot/grub/grub.cfg"
        bSuccess        = _ValToolsUtilities.runOsCommand(lLogger, sCommand, sDescription, bCriticalStep=True, bVerbose=True)
        if (not bSuccess):
            return 0

        lLogger.info("Running disablerecovery()")
        command=disablerecovery()
        if command ==1:
            lLogger.info("Successfully Lcp 3 policy written")
            return 1
        else:
            lLogger.error("Failed Writing LCP 3")	
            return 0


#+----------------------------------------------------------------------------+
            # LCP 4

def lcp4():
    lLogger.info( "\n")
    lLogger.info( " **********************************LCP4 PO PCONF Mismatch (Negative Test)**********************************")
    lLogger.info( "\n")
    lLogger.info( "Running echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
    Command=_os.system("echo PCR-00: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF > ./bad_pcr ")
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
            # LCP 5

def lcp5():
    lLogger.info( "\n")
    lLogger.info( " **********************************LCP5 PO MLE Signed***********************************")
    lLogger.info( "\n")
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
    lLogger.info(" Running lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle2.elt ./tboot_hash")
    SCommand="lcp_crtpolelt --create --type mle --ctrl 0x00 --minver 0 --out ./tbootmle5.elt ./tboot_hash"
    Command=subprocess.call(_shlex.split(SCommand))
    if (Command !=0):
        lLogger.error("Failed: Running lcp_crtpolelt --create --type mle --ctrl 0x00  --minver 0 --out ./tbootmle5.elt ./tboot_hash")
        return 0
    #MLE list creation
    lLogger.info("Running lcp_crtpollist --create --out ./list5.lst ./tbootmle5.elt")
    SCommand="lcp_crtpollist --create --out ./list5_sig.lst ./tbootmle5.elt"
    Command=subprocess.call(_shlex.split(SCommand))
    if (Command !=0):
        lLogger.error("Failed :Running lcp_crtpollist --create --out ./list5_sig.lst ./tbootmle5.elt")
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
        lLogger.info("Found LCP 2...Executing....")
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

