@echo off
set "GAME=%~dp0game_of_life.py"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 --version >nul 2>nul
    if not errorlevel 1 (
        py -3 "%GAME%"
        goto finish
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 (
        python "%GAME%"
        goto finish
    )
)

if exist "%USERPROFILE%\.venv\Scripts\python.exe" (
    "%USERPROFILE%\.venv\Scripts\python.exe" "%GAME%"
    goto finish
)

echo Python 3 was not found.
echo Install Python 3 from https://www.python.org/downloads/windows/
echo During installation, enable "Add python.exe to PATH".
echo The game uses Tkinter, which is included with the standard Windows installer.
pause
exit /b 1

:finish
if errorlevel 1 (
    echo.
    echo The game closed with an error.
    pause
)
