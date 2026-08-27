@echo off
title AbhiApp - Your Personal Digital Vault
color 0A

echo ========================================================
echo        AbhiApp - Your Personal Digital Vault
echo ========================================================
echo.
echo Starting AbhiApp Server on http://127.0.0.1:5000 ...
echo Default Account: abhi / AbhiApp@2026
echo.

start http://127.0.0.1:5000
python app.py
pause
