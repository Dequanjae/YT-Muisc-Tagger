@echo off
title Music Suite 2-in-1
echo ========================================
echo   Launching Music Suite 2-in-1...
echo ========================================
echo.
echo Checking dependencies...
pip install -r requirements.txt --quiet
echo Starting server and opening browser...
python combined_app.py
pause
