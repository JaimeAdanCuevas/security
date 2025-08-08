@echo off

Rem Update the PEPV-Tools Software
Rem
Rem $Id: UpdatePEPV-Tools.bat 2554 2013-09-26 17:33:53Z amr\dbraford $

set Log=UpdatePEPV-Tools.log

REM set Options=-rtpvz --chmod=u+rwX --ignore-errors --exclude=.svn -e "ssh -o batchMode=yes"

set Options=-rtpvz --exclude=.svn --ignore-errors -e "ssh -o batchMode=yes"

echo PEPV-Tools-Update > %Log%

if "%PEPV-ToolsRsync%"=="" (
  set PEPV-ToolsRsync=/cygdrive/c/Automation/pepv
)

echo. >> %Log%
echo PEPV_Tools root: %PEPV-ToolsRsync% >> %Log%

echo. >> %Log%
echo rsync PEPV-Tools >> %Log%

set I=0

:LOOP

  rsync %Options% %UpdateServer%:%UpdateDir%/PEPV_Tools/ %PEPV-ToolsRsync% >> %Log% 2>&1

  set Status=%errorlevel%

  if %Status% EQU 0 GOTO DONE

  ping localhost -n 2 > nul
  
  set /a I += 1

  echo Warning: Rsync Status: %Status%, Retry Count = %I% >> %Log%

  if %I% LSS 3 GOTO LOOP

  echo ERROR: Rsync Status: %Status%, Retry Count Exceeded >> %Log%

  exit %Status%

:DONE

echo Status %Status% >> %Log%
echo. >> %Log%

echo PEPV-Tools-Update Done >> %Log%

exit %Status%
