#!/bin/bash
#THIS FILE ADD PACKETS FOR THE SECURE CONNECTION IN THE CORPORATE NETWORK FOR LINUX OS
#
#For a safe installation of this file, give it all permissions, run
#'chmod 777 NetworkPatch_IT_Script.sh' or 'chmod +x NetworkPatch_IT_Script.sh'.
#
#To run the command on a terminal Linux'./NetworkPatch_IT_Script.sh'.
#
#If you have any errors or question about the command, please contact
#Oscar Reyes Espinosa or Jose Lucero Hernandez.

wget -4 -e use_proxy=no -q -O - http://isscorp.intel.com/IntelSM_BigFix/33570/package/scan/labscanaccount.sh | bash -s --
