@echo off

rem type CON > data.rtcm2

SET CONVBIN="rtklib_2.4.2\bin\convbin.exe"

IF EXIST %CONVBIN% (
  echo RTKlib convbin
  echo ==============
  mkdir logs
  del logs\data.obs
  %CONVBIN% -d logs data.rtcm2
  IF EXIST "logs\data.obs" (
    type logs\data.obs
  )
  echo ==============
)
del data.rtcm2

