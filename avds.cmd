@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONPATH=%PROJECT_DIR%src;%PYTHONPATH%"

if defined AVDS_PYTHON (
  "%AVDS_PYTHON%" -m avds.user_cli %*
) else if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
  "%PROJECT_DIR%.venv\Scripts\python.exe" -m avds.user_cli %*
) else (
  py -3 -m avds.user_cli %*
)

exit /b %ERRORLEVEL%
