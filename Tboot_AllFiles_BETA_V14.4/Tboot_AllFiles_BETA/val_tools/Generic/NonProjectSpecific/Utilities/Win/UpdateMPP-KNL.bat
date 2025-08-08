@echo off

Rem Update the MPP-KNL Software
Rem
Rem $Id: UpdateMPP-KNL.bat 1986 2012-05-11 03:34:33Z amr\sesmith $

set Log=UpdateMPP-KNL.log

REM set Options=-rtpvz --chmod=u+rwX --ignore-errors --exclude=.svn -e "ssh -o batchMode=yes"

set Options=-rtpvz --ignore-errors -e "ssh -o batchMode=yes"

echo MPP-KNL-Update > %Log%

if "%MPPKNLRsync%"=="" (
  set MPPKNLRsync=/cygdrive/c/Automation/gitclones/mpp-knl
)

echo. >> %Log%
echo MPP-KNL root: %MIVRsync% >> %Log%

echo. >> %Log%
echo rsync MPP-KNL >> %Log%

set I=0

:LOOP

  rsync %Options% %UpdateServer%:%UpdateDir%/mpp-knl/ %MPPKNLRsync% >> %Log% 2>&1

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

echo MPP-KNL-Update Done >> %Log%

exit %Status%
