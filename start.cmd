@echo off
setlocal
title VendorGuard AI - Native Windows Environment
cd /d "%~dp0"

echo =====================================================================
echo   VendorGuard AI - Native Windows Launcher (CMD)
echo   WSL is terminated. Running purely on Windows native Node ^& Python.
echo =====================================================================
echo.

node start-dev.js

endlocal
