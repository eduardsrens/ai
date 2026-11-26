@echo off
cd /d "%~dp0"
py blackjack.py
if errorlevel 1 pause
