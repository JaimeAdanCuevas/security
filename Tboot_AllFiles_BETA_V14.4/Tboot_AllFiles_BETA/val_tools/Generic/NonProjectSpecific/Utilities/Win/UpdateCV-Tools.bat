@echo off

Rem Update the cv_tools Software
Rem
Rem $Id: UpdateCV-Tools.bat 2033 2012-06-19 03:54:22Z amr\dbraford $

set Log=UpdateCV-Tools.log

REM set Options=-rtpvz --chmod=u+rwX --ignore-errors --exclude=.svn -e "ssh -o batchMode=yes"

set Options=-rtpvz --exclude=.svn --ignore-errors -e "ssh -o batchMode=yes"

echo CV-Tools-Update > %Log%

if "%CV-ToolsRsync%"=="" (
  set CV-ToolsRsync=/cygdrive/c/Automation/cv_tools
)

echo. >> %Log%
echo cv_tools root: %CV-ToolsRsync% >> %Log%

echo. >> %Log%
echo rsync CV-Tools >> %Log%

set I=0

:LOOP

  rsync %Options% %UpdateServer%:%UpdateDir%/cv_tools/ %CV-ToolsRsync% >> %Log% 2>&1

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

echo CV-Tools-Update Done >> %Log%

exit %Status%
