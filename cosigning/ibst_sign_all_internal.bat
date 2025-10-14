@echo off
echo =====================Sign OS Manifests Script ===================================

:: Use full absolute paths to avoid any relative path issues
set PY_PATH=C:\Users\jacuevas\Downloads\validation\security\security\.venv38\Scripts\python.exe
set IBST_DIR=C:\Users\jacuevas\Downloads\validation\security\security\cosigning\IBST_1.0.5758
set OVERRIDE_DIR=C:\Users\jacuevas\Downloads\validation\security\security\cosigning\Overrides
set KEY_DIR=C:\Users\jacuevas\Downloads\validation\security\security\cosigning\IBST_1.0.117\config
set OUTPUT_DIR=C:\Users\jacuevas\Downloads\validation\security\security\cosigning\Output
set INPUT_DIR=C:\Users\jacuevas\Downloads\validation\security\security\cosigning\Input

echo                 ################# Signing OS Kernel #################
"%PY_PATH%" "%IBST_DIR%\ibst.py" "%IBST_DIR%\config\CoSigningManifest.xml" --config_override "%OVERRIDE_DIR%\CoSigningManifest_OS_Yocto_override.xml" -s key="%KEY_DIR%\3k_test_key_private.pem" module_bin="%INPUT_DIR%\bootx64.efi" output_name="%OUTPUT_DIR%\bootx64.efi.bin"
if %errorlevel% neq 0 (
    echo ERROR: Failed to sign OS Kernel - Error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo                 ################# Signing bzImage #################
"%PY_PATH%" "%IBST_DIR%\ibst.py" "%IBST_DIR%\config\CoSigningManifest.xml" --config_override "%OVERRIDE_DIR%\CoSigningManifest_NL_Yocto_override.xml" -s key="%KEY_DIR%\3k_test_key_private.pem" module_bin="%INPUT_DIR%\bzImage" output_name="%OUTPUT_DIR%\bzimage.bin"
if %errorlevel% neq 0 (
    echo ERROR: Failed to sign bzImage - Error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo                 ################# Signing msrtest.efi tool #################
"%PY_PATH%" "%IBST_DIR%\ibst.py" "%IBST_DIR%\config\CoSigningManifest.xml" --config_override "%OVERRIDE_DIR%\CoSigningManifest_msrtest_override.xml" -s key="%KEY_DIR%\3k_test_key_private.pem" module_bin="%INPUT_DIR%\msrtest.efi" output_name="%OUTPUT_DIR%\msrtest.efi.bin"
if %errorlevel% neq 0 (
    echo ERROR: Failed to sign msrtest.efi - Error code: %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo Script completed successfully!
pause