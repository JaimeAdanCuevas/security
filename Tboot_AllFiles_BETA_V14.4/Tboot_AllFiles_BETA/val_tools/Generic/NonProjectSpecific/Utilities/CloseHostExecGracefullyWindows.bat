@echo off

Rem This finds and script kills the UVAT HostExec process

Rem $Id$

set Log=%~n0%.log

timeout /t 10
Rem set Cmd=powershell -command  "&{ Get-Process       | ForEach-Object { if ($_.ProcessName         -eq       'PipeCapture')     { $_.Kill()                  }}}"
set Cmd=powershell -command  "&{ Get-WmiObject Win32_Process | where {$_.ProcessName -match 'tclsh.exe'} | where {$_.CommandLine -match 'c:\\Automation\\bin\\HostExecWin.tcl -log C:\\Automation\\run\\HostExec.log' } | foreach {Stop-Process -force -id $_.ProcessId}}"

echo %DATE% %TIME% > %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

echo "Command completed with exit code " %ExitCode% >> %Log%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

exit %ExitStatus%
@echo off
