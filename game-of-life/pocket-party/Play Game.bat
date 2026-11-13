@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        py -3 server.py --open
        goto finish
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 (
        python server.py --open
        goto finish
    )
)

if exist "%USERPROFILE%\.venv\Scripts\python.exe" (
    "%USERPROFILE%\.venv\Scripts\python.exe" server.py --open
    goto finish
)

echo Python 3.10 or newer was not found.
echo Install Python 3 from https://www.python.org/downloads/windows/
echo During installation, enable "Add python.exe to PATH".
pause
exit /b 1

:finish
if errorlevel 1 (
    echo.
    echo Pocket Party could not start. See the message above.
    pause
)
