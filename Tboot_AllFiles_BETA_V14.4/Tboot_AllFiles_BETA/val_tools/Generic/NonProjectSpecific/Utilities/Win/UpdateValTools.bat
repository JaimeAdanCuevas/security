@echo off

Rem Update from the Val Tools via SCP
Rem
Rem $Id: UpdateValTools.bat 2017-03-31 12:59:32Z amr\aagiwal $

setlocal enabledelayedexpansion
:: Enables runtime variable expansion in side
:: of multiline command blocks, (), for !variables!

set LOG=UpdateValTools.log

echo Update ValTools > %LOG%
echo. >> %LOG%

if "%UpdateServer%"=="" (
  echo ERROR: No UpdateServer >> %LOG%
  exit 1
)

echo UpdateServer: %UpdateServer% >> %LOG%

if "%UpdateDir%"=="" (
  echo ERROR: No UpdateDir >> %LOG%
  exit 2
)

echo UpdateDir: %UpdateDir% >> %LOG%

if "%Site%"=="" (
  echo ERROR: No Site >> %LOG%
  exit 3
)

echo Site: %Site% >> %LOG%
echo. >> %LOG%

set Options=-rtpvz --ignore-errors --exclude=.svn -e "/cygdrive/C/cwRsync/bin/ssh -o batchMode=yes -o StrictHostKeyChecking=no" 

Rem Code Block to prevent over write of script by Update
(
  
  echo rsync Options %Options% >> %LOG%
  echo. >> %LOG%

  REM Note: this structure is because MS Batch does not support Labels in side of () 
  REM and there is no equivalent for break

  echo rsync %UpdateDir%/val_tools >> %LOG%

  set Status=-1

  for %%I in (1,1,3) Do (
    if !Status! NEQ 0 (
      rsync !Options! %UpdateServer%:%UpdateDir%/val_tools "/cygdrive/c/" >> %LOG% 2>&1
      set Status=!errorlevel!
      
      if !Status! NEQ 0 (
        rem Wait 1 sec
        ping localhost -n 2 > nul
  
        echo Warning: Rsync Tools Status: !Status!, Retry Count = %%I >> %LOG%
      )
    )
  )
  
  if !Status! NEQ 0 (
    echo ERROR: Rsync Tools Status: !Status!, Retry Count Exceeded >> %LOG%
    exit !Status!
  )
  echo Status !Status! >> %LOG%
  echo. >> %LOG%

  )
  echo Status !Status! >> %LOG%
  echo. >> %LOG%
  

  echo Update Automation Done >> %LOG%

  exit !Status!
)
