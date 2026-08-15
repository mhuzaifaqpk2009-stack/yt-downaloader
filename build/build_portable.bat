@echo off
REM ===========================================================================
REM  build_portable.bat
REM  Builds the portable single-file .exe using PyInstaller (--onefile).
REM  ffmpeg.exe is automatically downloaded and bundled inside the .exe so
REM  the app works fully offline — no internet needed after building.
REM  Output: dist\YT_Downloader.exe
REM ===========================================================================

setlocal

REM Ensure we run from the project root (one level up from this script's location)
pushd "%~dp0.."

echo.
echo ===================================================
echo   YT Downloader - Portable Build
echo ===================================================
echo.

REM --- Check Python ---
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.10 or 3.11 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

REM 1. Install dependencies
echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

REM 2. Fetch ffmpeg safely
echo [2/4] Fetching ffmpeg.exe for offline MP3 conversion...
python build\fetch_ffmpeg.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to fetch ffmpeg.
    exit /b 1
)

REM 3. Clean previous PyInstaller artifacts (preserves build scripts)
echo [3/4] Cleaning previous build artifacts...
if exist build\YT_Downloader_build rmdir /s /q build\YT_Downloader_build
if exist build\YT_Downloader rmdir /s /q build\YT_Downloader
if exist dist\YT_Downloader.exe del /q dist\YT_Downloader.exe

REM 4. Build with PyInstaller
echo [4/4] Building portable .exe with PyInstaller...
python -m PyInstaller build\YT_Downloader.spec --noconfirm --workpath build\YT_Downloader_build --distpath dist

# Build native messaging host executable
echo [5/5] Building native host executable (native_host.exe)...
python -m PyInstaller --onefile tools\native_host.py --name native_host --distpath dist
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

echo.
echo ===================================================
echo   Build complete!
echo   Output: dist\YT_Downloader.exe
echo.
echo   This single file includes:
echo     - The app GUI (Tkinter)
echo     - Python runtime + yt-dlp
echo     - ffmpeg.exe (for MP3 conversion)
echo.
echo   Copy it to a USB drive and run it on any
echo   Windows 10/11 PC - no installation needed.
echo ===================================================
echo.

REM Clean up build artifacts to save space
if exist build\YT_Downloader_build rmdir /s /q build\YT_Downloader_build

popd
endlocal