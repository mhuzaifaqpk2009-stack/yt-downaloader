# YT Downloader

A lightweight Windows desktop app for downloading YouTube videos as **MP4** (video, selectable resolution) or **MP3** (audio only). Built with Python + Tkinter, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp). No API key, no YouTube Data API.

---

## Features

- Paste any YouTube URL — watch, youtu.be, or Shorts links
- Fetch button shows video title, duration, channel, and available resolutions
- Choose **MP4 (video)** or **MP3 (audio only)**
- Pick resolution: 144p, 360p, 480p, 720p, 1080p, or Best Available
- Live progress bar with speed and ETA
- Cancel button to stop mid-download
- Choose output folder (defaults to a `Downloads` folder next to the app)
- ffmpeg is **bundled inside** both the portable .exe and the installer — no separate install needed
- Clean error messages — never crashes on bad URLs or network issues

---

## Project Structure

```
Youtube dowlaoder/
├── main.py                  # Tkinter GUI (entry point)
├── downloader.py            # yt-dlp wrapper (info extraction + download)
├── ffmpeg_utils.py          # ffmpeg detection & auto-download
├── requirements.txt         # Python dependencies (yt-dlp)
├── .gitignore
├── assets/
│   └── (optional app_icon.ico)
└── build/
    ├── YT_Downloader.spec   # PyInstaller spec → portable single-file .exe
    ├── installer.iss       # Inno Setup script → Windows installer
    ├── fetch_ffmpeg.py      # Auto-downloads ffmpeg.exe before building
    ├── build_portable.bat   # One-click: build portable .exe
    ├── build_installer.bat  # One-click: build installer .exe
    └── build_all.bat        # One-click: build both
```

---

## Running from Source (for development/testing)

### 1. Install Python

Install **Python 3.10 or 3.11** (64-bit) from [python.org](https://www.python.org/downloads/).
**Important:** During installation, check **"Add Python to PATH"**.

Verify:
```powershell
python --version
```

### 2. Install dependencies

```powershell
cd "c:\Users\_\OneDrive\Desktop\Youtube dowlaoder"
pip install -r requirements.txt
```

### 3. Run

```powershell
python main.py
```

---

## Building the Two Versions

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 or 3.11 (64-bit) | [python.org](https://www.python.org/downloads/) |
| PyInstaller | ≥ 6.0 | Installed automatically by the build script |
| Inno Setup | 6.x | [jrsoftware.org](https://jrsoftware.org/isdl.php) |

> **Python path check:** Make sure `python` and `pip` work in your terminal before building.
> If `python` opens the Microsoft Store, disable the Store alias in
> **Settings → Apps → Advanced app settings → App execution aliases**, or use the full path
> to your Python installation.

---

### Version 1 — Portable .exe (single file, runs from USB)

This produces a single `YT_Downloader.exe` that contains **everything**: the app, Python
runtime, yt-dlp, and ffmpeg.exe. Copy it to a USB drive and run on any Windows 10/11
PC without installing anything — no Python, no ffmpeg, no internet needed.

**Option A — One-click script:**
```powershell
.\build\build_portable.bat
```

**Option B — Manual commands:**
```powershell
pip install -r requirements.txt
pip install pyinstaller
python build\fetch_ffmpeg.py        # downloads ffmpeg.exe for bundling
pyinstaller build\YT_Downloader.spec --noconfirm --distpath dist
```

**Output:** `dist\YT_Downloader.exe`

---

### Version 2 — Windows Installer (Program Files, Start Menu, uninstaller)

This produces a `YT_Downloader_Installer.exe` that installs the app to Program Files,
creates Start Menu shortcuts (and optional Desktop shortcut), and registers an
uninstaller in Add/Remove Programs. The installer includes everything (Python,
yt-dlp, ffmpeg) — the user just installs and runs.

**Prerequisite:** The portable `.exe` must be built first (the installer wraps it).

**Option A — One-click script:**
```powershell
.\build\build_installer.bat
```

**Option B — Manual command (requires Inno Setup installed):**
```powershell
iscc build\installer.iss
```

**Output:** `dist\YT_Downloader_Installer.exe`

---

### Build Both at Once

```powershell
.\build\build_all.bat
```

This runs the portable build first, then the installer build. Both files end up in `dist\`.

---

## ffmpeg Notes

ffmpeg is required for MP3 conversion. **Both the portable and installer versions
already bundle ffmpeg.exe inside the .exe** — the build script auto-downloads it
before building and PyInstaller packages it inside.

At runtime, the app finds ffmpeg in this priority order:

1. **Inside the .exe** (PyInstaller temp directory `sys._MEIPASS`) — bundled at build time.
2. **Next to the app/exe** — if you manually place `ffmpeg.exe` in the same folder.
3. **System PATH** — if ffmpeg is installed system-wide.
4. **Auto-download** — as a last resort, if no ffmpeg is found, the app downloads a
   portable static ffmpeg.exe (~100 MB) to `%APPDATA%\YTDownloader\ffmpeg\`.
   This happens once and is cached.

So with the bundled approach, users never need to install ffmpeg separately.

---

## Performance & Low-Spec Notes

The app is designed to run well on old hardware (4 GB RAM, Intel i5-2540M):

- **Tkinter GUI** — no Electron, no web view, minimal memory footprint.
- **Single worker thread** — only one background operation at a time.
- **64 KB download chunks** — low memory usage even for large files.
- **yt-dlp instead of pytube** — far more resilient to YouTube's frequent backend changes.
- **No background services** — the app does nothing when the window is closed.
- **Excluded heavy packages** — numpy, scipy, matplotlib, Qt etc. are stripped from the bundle.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Install Python 3.10/3.11 and check "Add to PATH", or use full path |
| `yt-dlp` not found | Run `pip install -r requirements.txt` |
| PyInstaller build fails | `pip install pyinstaller` first; ensure Python is 64-bit |
| Inno Setup not found | Install Inno Setup 6 from [jrsoftware.org](https://jrsoftware.org/isdl.php) |
| Antivirus flags the exe | This is a false positive common with PyInstaller builds. Use `--onedir` mode or sign the exe. You can also set `upx=False` in the spec. |
| YouTube rate-limits (HTTP 429) | Wait a few minutes between many downloads |
| Download fails on a specific video | The video may be private, age-restricted, or region-locked |

---

## License & Disclaimer

This tool is for personal use. Respect YouTube's Terms of Service and copyright laws.
Only download content you have the right to download.

---

## Browser integration (Chrome / Edge)

This project includes a small Chrome/Edge extension that adds a right-click menu
"Open with YT Downloader" on YouTube pages. The extension sends the selected
YouTube URL to the installed native messaging host, which forwards it to the
already-running app (or launches the app if needed). The app brings itself to the
front and inserts the URL into the existing field, then triggers Fetch without
starting a download automatically.

Files:
- `extensions/yt_downloader_extension/manifest.json`
- `extensions/yt_downloader_extension/background.js`
- `tools/native_messaging/com.yt_downloader.host.json`

Install the extension (developer mode):

1. Open `chrome://extensions/` or `edge://extensions/`.
2. Enable "Developer mode".
3. Click "Load unpacked" and select the `extensions/yt_downloader_extension` folder.
4. Copy the generated extension ID from the extensions page.
5. Update the `allowed_origins` value in `tools/native_messaging/com.yt_downloader.host.json`
   to `chrome-extension://<EXTENSION_ID>/` and install the host manifest in the system registry.

Native Messaging setup:

1. Build the portable `.exe` or installer so you have `YT_Downloader.exe` and `native_host.exe`.
2. Install the app so the native host is placed in the app folder.
3. Add the registry entries for Chrome and Edge under:
   - `HKLM\Software\Google\Chrome\NativeMessagingHosts\com.yt_downloader.host`
   - `HKLM\Software\Microsoft\Edge\NativeMessagingHosts\com.yt_downloader.host`
4. Point each value to the installed manifest path, for example:
   `C:\Program Files\YT Downloader\com.yt_downloader.host.json`

Behavior:
- The extension uses `info.linkUrl` when it is a valid YouTube video URL; otherwise it falls
  back to the current tab URL.
- It sends the URL via `chrome.runtime.sendNativeMessage()` to the native host.
- The host forwards the payload to the running app over the localhost IPC socket.
- The app focuses itself and fills the existing URL field, then triggers Fetch.

Supported URL patterns: `youtube.com/watch*`, `youtu.be/*`, `youtube.com/shorts/*`.

