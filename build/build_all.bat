@echo off
REM ===========================================================================
REM  build_all.bat
REM  Builds BOTH the portable .exe and the Windows installer in one go.
REM  ffmpeg.exe is auto-downloaded and bundled inside the portable .exe,
REM  so both versions work fully offline after building.
REM  Output:
REM    dist\YT_Downloader.exe           (portable — single file, USB-ready)
REM    dist\YT_Downloader_Installer.exe (installer — Program Files + shortcuts)
REM ===========================================================================

setlocal

echo.
echo ===================================================
echo   YT Downloader - Full Build (Portable + Installer)
echo ===================================================
echo.

REM Step 1: Check if required files exist
if not exist "%~dp0build_portable.bat" (
    echo [ERROR] Cannot find 'build_portable.bat' in the current folder!
    echo Make sure all build scripts are in the same directory.
    pause
    exit /b 1
)

if not exist "%~dp0build_installer.bat" (
    echo [ERROR] Cannot find 'build_installer.bat' in the current folder!
    echo Make sure all build scripts are in the same directory.
    pause
    exit /b 1
)

REM Step 2: Build the portable exe (includes ffmpeg fetch)
echo Starting build_portable.bat...
call "%~dp0build_portable.bat"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Portable build failed. Aborting.
    echo Please read the error messages above to see what went wrong.
    pause
    exit /b 1
)

echo.
echo --- Portable build done. Starting installer build... ---
echo.

REM Step 3: Build the installer
echo Starting build_installer.bat...
call "%~dp0build_installer.bat"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installer build failed.
    echo The portable .exe was still built successfully.
    echo Please read the error messages above to see what went wrong.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   All builds complete!
echo.
echo   Portable:  dist\YT_Downloader.exe
echo              (single file — copy to USB, run anywhere)
echo.
echo   Installer: dist\YT_Downloader_Installer.exe
echo              (installs to Program Files, Start Menu
echo               shortcut, optional Desktop, uninstaller)
echo.
echo   Both include ffmpeg.exe bundled inside.
echo   No Python, no ffmpeg, no internet needed to use.
echo ===================================================
echo.

pause

endlocal