@echo off

Rem Update the MIV Software
Rem
Rem $Id: UpdateMIV.bat 1986 2012-05-11 03:34:33Z amr\dbraford $

set Log=UpdateMIV.log

REM set Options=-rtpvz --chmod=u+rwX --ignore-errors --exclude=.svn -e "ssh -o batchMode=yes"

set Options=-rtpvz --exclude=.svn --ignore-errors -e "/cygdrive/C/cwRsync/bin/ssh -o batchMode=yes"

echo MIV-Update > %Log%

if "%MIVRsync%"=="" (
  set MIVRsync=/cygdrive/c/Program Files/Intel/MIV
)

echo. >> %Log%
echo MIV root: %MIVRsync% >> %Log%

echo. >> %Log%
echo rsync MIV >> %Log%

set I=0

:LOOP

  rsync %Options% %UpdateServer%:%UpdateDir%/MivSoftware/ %MIVRsync% >> %Log% 2>&1

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

echo MIV-Update Done >> %Log%

exit %Status%
