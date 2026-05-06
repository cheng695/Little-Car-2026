@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_jlink.ps1" %*
set "DOWNLOAD_EXIT_CODE=%ERRORLEVEL%"

if not "%DOWNLOAD_EXIT_CODE%"=="0" (
    echo.
    echo Download failed with exit code %DOWNLOAD_EXIT_CODE%.
    pause
)

exit /b %DOWNLOAD_EXIT_CODE%
