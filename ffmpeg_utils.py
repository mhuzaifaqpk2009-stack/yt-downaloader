"""
ffmpeg_utils.py

Handles detection and on-demand download of a portable ffmpeg.exe so that
MP3 conversion works out of the box without requiring the user to install
anything manually.

Detection order:
  1. ffmpeg.exe shipped next to the app (bundled portable copy)
  2. ffmpeg available on the system PATH
  3. Cached copy in the user's AppData folder (auto-downloaded once)
  4. If none found, auto-download a portable static build to the cache.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import tempfile
import ssl

# A reliable static-ffmpeg build for Windows (64-bit).
# This is the BtbN/ffscripts release – a well-known, frequently updated build.
FFMPEG_DOWNLOAD_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

# Cache directory in the user's AppData so we only download once.
_CACHE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "YTDownloader", "ffmpeg")


def _is_frozen():
    """True when running as a PyInstaller-bundled exe."""
    return getattr(sys, "frozen", False)


def _app_dir():
    """Directory the application (or frozen exe) lives in."""
    if _is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _find_bundled():
    """Look for ffmpeg.exe bundled with the app.

    When running as a PyInstaller --onefile exe, bundled data files are
    extracted to a temp directory accessible via sys._MEIPASS.
    Also checks the app/exe directory for copies placed there (e.g. by
    the installer).
    """
    exe_name = "ffmpeg.exe"
    candidates = [
        os.path.join(_app_dir(), exe_name),
        os.path.join(_app_dir(), "ffmpeg", exe_name),
        os.path.join(_app_dir(), "bin", exe_name),
    ]
    # PyInstaller --onefile extracts bundled files to sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, os.path.join(meipass, exe_name))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _find_in_path():
    """Check the system PATH for ffmpeg."""
    found = shutil.which("ffmpeg")
    if found and os.path.isfile(found):
        return found
    return None


def _find_cached():
    """Look for the previously auto-downloaded copy."""
    exe_path = os.path.join(_CACHE_DIR, "ffmpeg.exe")
    if os.path.isfile(exe_path):
        return exe_path
    return None


def is_ffmpeg_available():
    """Return True if ffmpeg can be found right now without downloading."""
    return _find_cached() or _find_bundled() or _find_in_path() is not None


def find_ffmpeg():
    """
    Return the path to a usable ffmpeg.exe, or None if none is available yet.

    Call this when you just need to check / use ffmpeg without triggering a
    download.  Use ensure_ffmpeg() when you want to auto-download if missing.
    """
    for finder in (_find_cached, _find_bundled, _find_in_path):
        path = finder()
        if path:
            return os.path.abspath(path)
    return None


def download_ffmpeg(progress_callback=None):
    """
    Download and cache a portable static ffmpeg.exe.

    Args:
        progress_callback: callable(downloaded_bytes, total_bytes) or None.
                          Called periodically during the download.

    Returns:
        Path to the extracted ffmpeg.exe on success.

    Raises:
        RuntimeError if the download or extraction fails.
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    exe_path = os.path.join(_CACHE_DIR, "ffmpeg.exe")

    # Already cached?  Just return it.
    if os.path.isfile(exe_path):
        return exe_path

    zip_path = os.path.join(_CACHE_DIR, "ffmpeg_download.zip")

    # Use a non-strict SSL context for environments with older certificates.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            FFMPEG_DOWNLOAD_URL, headers={"User-Agent": "YT-Downloader/1.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536  # 64 KB chunks – low memory footprint

            with open(zip_path, "wb") as f:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress_callback:
                        progress_callback(downloaded, total)

        # Extract just the ffmpeg.exe binary from the zip archive.
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                basename = os.path.basename(name).lower()
                if basename == "ffmpeg.exe":
                    # Extract directly into our cache dir.
                    with zf.open(name) as src, open(exe_path, "wb") as dst:
                        shutil.copyfileobj(src, dst, length=chunk)
                    break
            else:
                raise RuntimeError(
                    "ffmpeg.exe was not found inside the downloaded archive."
                )
    except Exception as exc:
        raise RuntimeError(f"Failed to download ffmpeg: {exc}") from exc
    finally:
        # Clean up the zip to save disk space.
        if os.path.isfile(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass

    if not os.path.isfile(exe_path):
        raise RuntimeError("ffmpeg.exe extraction completed but file is missing.")

    return exe_path


def ensure_ffmpeg(progress_callback=None):
    """
    Guarantee that ffmpeg.exe is available and return its path.

    If ffmpeg is already found (bundled / PATH / cached) it is returned
    immediately.  Otherwise the portable build is downloaded and cached.

    Args:
        progress_callback: callable(downloaded_bytes, total_bytes) or None.

    Returns:
        Absolute path to a usable ffmpeg.exe.
    """
    existing = find_ffmpeg()
    if existing:
        return existing
    return download_ffmpeg(progress_callback)
