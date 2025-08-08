@echo off
::Script wrapper for CleanUpTestSshDp Python script.

set PYTHON_SCRIPT="%~dp0/cleanup_ssh_dp.py"
python %PYTHON_SCRIPT% %*

exit /B %errorlevel% 
