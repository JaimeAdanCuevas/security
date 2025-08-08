@echo off

Rem Update from the PythonSV SVN Directory
Rem
Rem Assumes %UpdateServer%:%UpdateDir% is common for PythonSV and UVAT
Rem
Rem $Id: UpdatePythonSv.bat 221 2017-03-31 12:58:13Z amr\aagiwal $

set Log=UpdatePythonSV.log

REM set Options=-rtpvz --chmod=u+rwX --ignore-errors --exclude=.svn -e "ssh -o batchMode=yes -o StrictHostKeyChecking=no"

set Options=-rtpvz --delete --exclude=.svn --ignore-errors -e "/cygdrive/C/cwRsync/bin/ssh -o batchMode=yes -o StrictHostKeyChecking=no"

if "%2"=="SQ" (
  set Revision=PythonSVSQ
) else (
  set Revision=PythonSV
)

echo PythonSV-Update > %Log%

echo GetSvnInfo for %UpdateDir%/PythonSV >> %LOG%

set Status=-1

for %%I in (1,2,3) Do (
  if %Status% NEQ 0 (
    ssh -o batchMode=yes -o StrictHostKeyChecking=no %UpdateServer% %Tools%/bin/GetSvnInfo %UpdateDir%/%Revision% >> %LOG% 2>&1
    set Status=%errorlevel%
    
    if %Status% NEQ 0 (
      ping localhost -n 2 > nul

      echo Warning: SSH GetSvnInfo Status: %Status%, Retry Count = %%I >> %LOG%
    )
  )
)
if %Status% NEQ 0 (
  echo ERROR: SSH GetSvnInfo Status: %Status%, Retry Count Exceeded >> %LOG%
  exit %Status%
)
echo Status %Status% >> %LOG%
echo. >> %LOG%

if "%PythonSvRsync%"=="" (
  set PythonSvRsync=/cygdrive/c/PythonSV
)

if "%PythonSv%"=="" (
  set PythonSv=C:\PythonSV
)

echo. >> %Log%
echo PythonSV root: %PythonSvRsync% >> %Log%

echo. >> %Log%
echo rsync PythonSV >> %Log%

set Status=-1

for %%I in (1,2,3) Do (
  if %Status% NEQ 0 (
    rsync %Options% %UpdateServer%:%UpdateDir%/%Revision%/ %PythonSvRsync% >> %LOG% 2>&1
    set Status=%errorlevel%
    
    if %Status% NEQ 0 (
      ping localhost -n 2 > nul

      echo Warning: SCP HostExec Status: %Status%, Retry Count = %%I >> %LOG%
    )
  )
)

if %Status% NEQ 0 (
  echo ERROR: SCP HostExec Status: %Status%, Retry Count Exceeded >> %LOG%
  exit %Status%
)
echo Status %Status% >> %LOG%
echo. >> %LOG%

if exist "%PythonSV%\__install__\installpath.py" (
  echo Run installpath.py >> %Log%

  python "%PythonSV%\__install__\installpath.py" --auto >> %Log% 2>&1

  set Status=%errorlevel%
  echo Status %Status% >> %Log%
  echo. >> %Log%
)

echo. >> %Log%
echo Run %NvmTools%\fixITP_pypi.py >> %Log%
echo. >> %Log%

fixITP_pypi.py >>  %Log%

set Status=%errorlevel%

if %Status% NEQ 0 (
  echo ERROR: fixITP_pypi.py returned Error %Status% >> %LOG%
  exit %Status%
)

echo. >> %Log%
echo UpdatePythonSv Done >> %Log%

echo PythonSV-Update Done to %Revision% >> %Log%

exit %Status%
