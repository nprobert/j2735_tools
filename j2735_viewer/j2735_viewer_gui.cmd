@echo off
set pwd=%cd%
echo
set PYTHONPATH=..\classes;..\classes\j2735
echo %PYTHONPATH%

python j2735_viewer_gui.py %*
rem append with "| clip" to get output into clipboard
