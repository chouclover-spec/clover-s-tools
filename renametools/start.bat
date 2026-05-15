@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
py image_renamer.py
pause
