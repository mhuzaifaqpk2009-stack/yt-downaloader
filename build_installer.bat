@echo off
REM ===========================================================================
REM  build_installer.bat
REM  Builds the Windows installer (.exe) using Inno Setup.
REM  Prerequisite: The portable .exe must already be built (run build_portable.bat
REM  or build_all.bat first). Also requires Inno Setup to be installed.
REM ===========================================================================

setlocal
@echo on
pushd "%~dp0.."

set "ISS_FILE=%~dp0installer.iss"

echo [DEBUG] START build_installer.bat

echo.
echo ===================================================
echo   YT Downloader - Installer Build
echo ===================================================
echo.

echo [DEBUG] checking dist\YT_Downloader.exe
REM --- Check that portable exe exists ---
if not exist "dist\YT_Downloader.exe" goto :no_portable

echo [DEBUG] portable exe exists

echo Using portable executable: dist\YT_Downloader.exe

goto :has_portable

:no_portable
echo [ERROR] dist\YT_Downloader.exe not found.
echo Please run build_portable.bat or build_all.bat first.
exit /b 1

:has_portable

REM --- Locate Inno Setup compiler (iscc) ---
set "ISCC="
set "ISS_X86=C:\Progra~2\Inno Setup 6\ISCC.exe"
set "ISS_X64=C:\Progra~1\Inno Setup 6\ISCC.exe"
echo [DEBUG] checking ISS_X86=%ISS_X86%
echo [DEBUG] checking ISS_X64=%ISS_X64%
if exist "%ISS_X86%" set "ISCC=C:\Progra~2\Inno Setup 6\ISCC.exe"
if exist "%ISS_X64%" set "ISCC=C:\Progra~1\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" goto :find_iscc

goto :after_iscc

:find_iscc
where iscc >nul 2>nul
if %ERRORLEVEL% neq 0 goto :no_iscc
set "ISCC=iscc"

:after_iscc

echo Using Inno Setup: %ISCC%

echo Building installer...
"%ISCC%" "%ISS_FILE%"
if %ERRORLEVEL% neq 0 goto :build_failed

echo.
echo ===================================================
echo   Installer build complete!
echo   Output: dist\YT_Downloader_Installer.exe
echo.
echo   Installing this .exe will:
echo     - Install to Program Files\YT Downloader
echo     - Create Start Menu shortcut
echo     - Optional Desktop shortcut
echo     - Register uninstaller in Add/Remove Programs
echo.
echo   The installer includes everything (Python, yt-dlp,
echo   ffmpeg) — no internet needed after installation.
echo ===================================================
echo.

popd
endlocal

goto :eof

:build_failed
echo [ERROR] Inno Setup compilation failed.
popd
exit /b 1

:no_iscc
echo [ERROR] Inno Setup compiler (iscc.exe) not found.
echo.
echo Please install Inno Setup (free) from: https://jrsoftware.org/isdl.php
echo After installation, this script will find it automatically.
popd
exit /b 1

