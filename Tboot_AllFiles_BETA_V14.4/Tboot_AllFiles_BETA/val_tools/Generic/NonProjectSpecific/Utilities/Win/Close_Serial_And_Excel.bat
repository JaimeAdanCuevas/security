@echo off

Rem This script kills processes that may be running and need to be closed out

Rem $Id: UVAT_Close_Serial_And_Excel.bat 2228 2012-11-07 23:23:10Z amr\dbraford $

set Log=%~n0%.log

set Cmd=powershell -command  "&{ Get-Process | ForEach-Object { if ($_.ProcessName -eq 'PipeCapture') { $_.Kill() }}}"

echo %DATE% %TIME% >> %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

set Cmd=powershell -command  "&{ Get-Process | ForEach-Object { if ($_.ProcessName -eq 'ttermpro') { $_.Kill() }}}"

echo %DATE% %TIME% >> %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

set Cmd=powershell -command  "&{ Get-Process | ForEach-Object { if ($_.ProcessName -eq 'hypertrm') { $_.Kill() }}}"

echo %DATE% %TIME% >> %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

set Cmd=powershell -command  "&{ Get-Process | ForEach-Object { if ($_.ProcessName -eq 'putty') { $_.Kill() }}}"

echo %DATE% %TIME% >> %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

set Cmd=powershell -command  "&{ Get-Process | ForEach-Object { if ($_.ProcessName -eq 'excel') { $_.Kill() }}}"

echo %DATE% %TIME% >> %Log%
echo %Cmd% >> %Log%
%Cmd%

set /a ExitCode = %errorlevel%

if %ExitCode% neq 0 (
    set /a ExitStatus = ExitStatus + 1
    echo %DATE% %TIME% >> %Log%
    echo Error: Exit Code %ExitCode% >> %Log%
)

exit %ExitStatus%
@echo off
