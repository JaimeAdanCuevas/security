@echo off

Rem Log Basic Info
Rem
Rem $Id: LogBasicInfo.bat 1318 2010-12-16 20:12:29Z amr\dbraford $

set Log=LogBasicInfo.log

echo Collect Basic System information > %Log%
echo. >> %Log%
echo Environment >> %Log%
echo. >> %Log%

set >> %Log%

echo. >> %Log%
echo Collect SVN Info Files >> %Log%
echo. >> %Log%

if exist C:\PythonSV (
  echo. >> %Log%
  echo Get a copy of PythonSV_SVN_Info.log >> %Log%
  copy /Y C:\PythonSV\svninfo.log PythonSV_SVN_Info.log >> %Log% 2>>&1
)

echo. >> %Log%
echo Collect Basic System information, Done >> %Log%

exit 0
