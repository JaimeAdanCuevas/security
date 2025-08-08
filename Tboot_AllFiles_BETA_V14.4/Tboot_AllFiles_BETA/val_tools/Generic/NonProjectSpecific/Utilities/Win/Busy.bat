@echo off

Set N=5
Set M=1
Set Tag=Tick
set Code=0

if NOT "%1" == "" (
  set N=%1
)

if NOT "%2" == "" (
  set M=%2
)

if NOT "%3" == "" (
  set Tag=%3
)

if NOT "%4" == "" (
  set Code=%4
)

set I=0

:Top1

if %I% GEQ %N% goto End1

  echo %Tag% %I%

  Set J=0

  :Top2

  if %J% GEQ %M% goto End2

    ping -n 2 127.0.0.1 > NUL

    set /a J=J+1

    goto Top2

  :End2

  set /a I=I+1

  goto Top1 

:End1


Exit %Code%