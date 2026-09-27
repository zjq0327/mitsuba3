@echo off
setlocal
set "PATH=%~dp0..\..\build\Release;%PATH%"
set "PYTHONPATH=%~dp0..\..\build\Release\python"
"%~dp0.venv\Scripts\python.exe" "%~dp0verify.py"
exit /b %errorlevel%
