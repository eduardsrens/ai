@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 server.py --open
    goto finish
)
where python >nul 2>nul
if not errorlevel 1 (
    python server.py --open
    goto finish
)
echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH" during installation.
pause
exit /b 1
:finish
if errorlevel 1 (
    echo.
    echo Pocket Party could not start. See the message above.
    pause
)
