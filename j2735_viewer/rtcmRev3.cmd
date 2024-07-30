@echo off

rem type CON > data.rtcm3

SET CONVBIN="RTKLIB_bin\bin\convbin.exe"

IF EXIST %CONVBIN% (
  echo RTKlib convbin
  echo ==============
  mkdir logs
  del logs\data.obs
  %CONVBIN% -d logs data.rtcm3
  IF EXIST "logs\data.obs" (
    type logs\data.obs
  )
  echo ==============
)
del data.rtcm3

