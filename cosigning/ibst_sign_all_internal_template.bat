
@REM Script to run IBST to sign ME Region and BIOS Region Images
@REM Sign  RBE, BUP, PMC Patch in ME Region, inserting manifests for each.  Creates ME Region Key Manifest
@REM Creates manifests  for ACM and FIT Patch.


@REM INTEL CONFIDENTIAL
@REM Copyright (c) 2016 - 2019, Intel Corporation. <BR>
@REM
@REM The source code contained or described herein and all documents related to the
@REM source code ("Material") are owned by Intel Corporation or its suppliers or
@REM licensors. Title to the Material remains with Intel Corporation or its suppliers
@REM and licensors. The Material may contain trade secrets and proprietary    and
@REM confidential information of Intel Corporation and its suppliers and licensors,
@REM and is protected by worldwide copyright and trade secret laws and treaty
@REM provisions. No part of the Material may be used, copied, reproduced, modified,
@REM published, uploaded, posted, transmitted, distributed, or disclosed in any way
@REM without Intel's prior express written permission.
@REM
@REM No license under any patent, copyright, trade secret or other intellectual
@REM property right is granted to or conferred upon you by disclosure or delivery
@REM of the Materials, either expressly, by implication, inducement, estoppel or
@REM otherwise. Any license under such intellectual property rights must be
@REM express and approved by Intel in writing.
@REM
@REM Unless otherwise agreed by Intel in writing, you may not remove or alter
@REM this notice or any other notice embedded in Materials by Intel or
@REM Intel's suppliers or licensors in any way.
@REM



echo off

::Path to Python install
set PY_PATH=C:\Python38

::Path to IBST installation
set IBST_PATH=<<path to \ibst_batch_file_keys_overrides>>\Ibst_sps5.0_1.0.846\IbstTool

::Path to IBST override files
set OVERRIDE_PATH=<<path to \ibst_batch_file_keys_overrides>>\Overrides

::Path to folder containing keys
set KEY_PATH=<<path to \ibst_batch_file_keys_overrides>>\IBST_1.0.117\config

::Path to folder to store output
set OUTPUT_PATH=<<path to \ibst_batch_file_keys_overrides>>\Output

::Path to folder containing ME Region.bin file #ignore this
set ME_REGION_PATH=<<path to \ibst_batch_file_keys_overrides>>\Input

::Path to PMC PATCH (pmcp.bin) # ignore this
set PMCP_PATH=<<path to pmc binary>>

::Path to OS image
set OS_PATH=<<path to \ibst_batch_file_keys_overrides>>\Input

pushd  %IBST_PATH%


echo =====================IBST  Test Script ===================================
echo 	@@@@@@@@@@@@@@@@@  Signing  ME Region  Firmware @@@@@@@@@@@@@@@@@@@@@@@
echo 		################# Signing RBE and BUP  in MERegion.bin #################

%PY_PATH%/python.exe %IBST_PATH%/ibst.py  config/CoSign.xml --config_override %OVERRIDE_PATH%/CoSign_override_RBE_BUP_internal.xml -s cosign_key="%KEY_PATH%/3k_test_key_private.pem"  input_file="%ME_REGION_PATH%/MeRegion.bin" output_name="%OUTPUT_PATH%/MeRegion.bin"

echo 		################# RBE and BUP Done #################

echo 		################# Signing PMC Patch #################

%PY_PATH%/python.exe %IBST_PATH%/ibst.py  config/CoSign.xml --config_override %OVERRIDE_PATH%/CoSign_override_PMCP_With_Footer_internal.xml  -s cosign_key="%KEY_PATH%/3k_test_key_private.pem"   input_file="%PMCP_PATH%/CDFH_A0_PMC_FW_000.02.01.1011_ProdSigned_pmcp.bin" output_name="%OUTPUT_PATH%/CDFH_A0_PMC_FW_000.02.01.1011_ProdSigned_pmcp.bin"

echo 		################# PMCP Done #################

echo 		################# Signing ME Region Key manifest #################

%PY_PATH%/python.exe %IBST_PATH%/ibst.py  config/OemKeyManifest.xml --skip_valid --config_override %OVERRIDE_PATH%/OemKeyManifest_override_all_keys_os_internal.xml ^
-s key="%KEY_PATH%/3k_test_key_private.pem"   ^
 rbe_bup_key="%KEY_PATH%/3k_test_key_private.pem" ^
 pmc_key="%KEY_PATH%/3k_test_key_private.pem"   ^
 oem_debug_key="%KEY_PATH%/3k_test_key_private.pem" ^
 idlm_key="%KEY_PATH%/3k_test_key_private.pem" ^
 os_key="%KEY_PATH%/3k_test_key_private.pem" ^
 netl_key="%KEY_PATH%/3k_test_key_private.pem" ^
 fd0v_key="%KEY_PATH%/3k_test_key_private.pem" ^
 output_name="%OUTPUT_PATH%/oemkeymn2_3K_KEY2_COS.bin" 

@REM echo 		###############  ME Region Key Manifest Done ####################


@REM echo 	@@@@@@@@@@@@@  ME Region Firmware Steps Done @@@@@@@@@@@@@@@@@@@@
@REM echo.

@REM echo 	@@@@@@@@@@@ Signing BIOS Region Images  @@@@@@@@@@@@@@@@@@@@@@

@REM echo 		################# Signing ACM #################

@REM %PY_PATH%/python ./ibst.py  config/CoSigningManifest.xml --config_override %OVERRIDE_PATH%/CoSigningManifest_override_ACM_internal.xml  -s key="%KEY_PATH%/ACM_3K_PRIVATE.pem" binary_hash="5fac83cd5a125bf65d333eea4357845b95b6e087b1c80337c10e8e2473ab2ebb" output_name="%OUTPUT_PATH%/ACMM_internal.bin" 
             
@REM echo 		################# ACM Done #################

@REM echo 		################# Signing FIT Patch #################

@REM %PY_PATH%/python ./ibst.py  config/CoSigningManifest.xml --config_override %OVERRIDE_PATH%/CoSigningManifest_override_FITP_internal.xml  -s key="%KEY_PATH%/FITP_3K_PRIVATE.pem" binary_hash="1a2848d6ad5a0943a85f7cfa2a2b40322c8b6c95f85fd97bb5d3eed108f189e5"  output_name="%OUTPUT_PATH%/FPM_internal.bin"
             
@REM echo 		################# FIT Patch Done #################

@REM echo  	@@@@@@@@@@@@@@ BIOS Images Done  @@@@@@@@@@@@@@@@@

echo 		################# Signing OS Kernel #################
%PY_PATH%/python %IBST_PATH%\ibst.py  config/CoSigningManifest.xml --config_override %OVERRIDE_PATH%/CoSigningManifest_OS_Yocto_override.xml  -s key="%KEY_PATH%/3k_test_key_private.pem"  module_bin="%OS_PATH%\bootx64.efi" output_name="%OUTPUT_PATH%/bootx64.efi.bin"                 


echo 		################# Signing bootx64.efi #################
%PY_PATH%/python %IBST_PATH%\ibst.py  config/CoSigningManifest.xml --config_override %OVERRIDE_PATH%/CoSigningManifest_NL_Yocto_override.xml  -s key="%KEY_PATH%/3k_test_key_private.pem"  module_bin="%OS_PATH%\bzImage" output_name="%OUTPUT_PATH%/bzImage.bin" 

popd 