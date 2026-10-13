@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || (echo Python 3 is required. & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (pause & exit /b 1)
)
set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m trace_monitor
if errorlevel 1 pause
