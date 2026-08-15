# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for YT Downloader – portable single-file build.

Build:
    pyinstaller YT_Downloader.spec --noconfirm

Output:
    dist/YT_Downloader.exe   (one standalone .exe, no installation needed)
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# Collect all yt-dlp submodules so they're included in the bundle.
yt_dlp_hidden = collect_submodules("yt_dlp")

# ── Project root ────────────────────────────────────────────────────────
# NOTE: __file__ is not defined in .spec files. PyInstaller is always
# invoked from the project root, so use the current working directory.
_PROJECT_ROOT = os.getcwd()

# ── Bundle ffmpeg.exe inside the .exe so MP3 conversion works offline ──
# The build script (build/fetch_ffmpeg.py) downloads a portable static
# ffmpeg.exe to the project root before running PyInstaller.
_ffmpeg_path = os.path.join(_PROJECT_ROOT, "ffmpeg.exe")
_datas = []
if os.path.isfile(_ffmpeg_path):
    _datas.append((_ffmpeg_path, "."))
    print(f"[spec] Bundling ffmpeg.exe: {_ffmpeg_path}")
else:
    print("[spec] WARNING: ffmpeg.exe not found — app will auto-download at runtime")

block_cipher = None

a = Analysis(
    [os.path.join(_PROJECT_ROOT, "main.py")],
    pathex=[_PROJECT_ROOT],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # yt-dlp submodules (collected dynamically above)
        *yt_dlp_hidden,
        # Standard library modules sometimes missed by the static analysis
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "http.client",
        "urllib.request",
        "urllib.error",
        "ssl",
        "certifi",
        "mimetypes",
        "multiprocessing",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip heavy, unused modules to keep the exe smaller
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "pytest",
        "IPython",
        "jupyter",
        "notebook",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="YT_Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # UPX can sometimes cause issues with antivirus false-positives.
    # If your AV flags the exe, set upx_exclude or upx=False.
    upx_exclude=[
        "vcruntime140.dll",
        "python3.dll",
    ],
    runtime_tmpdir=None,
    console=False,          # GUI app – no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Optional icon – create assets/app_icon.ico to use it.
    # The build still works without the icon file.
    icon="assets/app_icon.ico" if __import__("os").path.exists("assets/app_icon.ico") else None,
)
