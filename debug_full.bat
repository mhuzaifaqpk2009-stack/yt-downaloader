@echo off
setlocal
set "ISCC="
set "ISS_X86=C:\Progra~2\Inno Setup 6\ISCC.exe"
set "ISS_X64=C:\Progra~1\Inno Setup 6\ISCC.exe"
echo [DEBUG] ISS_X86=%ISS_X86%
echo [DEBUG] ISS_X64=%ISS_X64%
if exist "%ISS_X86%" set "ISCC=%ISS_X86%"
echo [DEBUG] after X86 ISCC=%ISCC%
if exist "%ISS_X64%" set "ISCC=%ISS_X64%"
echo [DEBUG] after X64 ISCC=%ISCC%
if "%ISCC%"=="" (
    where iscc >nul 2>nul
    echo errorlevel=%ERRORLEVEL%
    if errorlevel 1 (
        echo [ERROR] Inno Setup compiler (iscc.exe) not found.
        echo.
        echo Please install Inno Setup (free) from: https://jrsoftware.org/isdl.php
        exit /b 1
    )
    set "ISCC=iscc"
)
echo [DEBUG] final ISCC=%ISCC%
endlocal
