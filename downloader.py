"""
downloader.py

Thin wrapper around yt-dlp that:
  - extracts video info (title, available resolutions)
  - downloads in a chosen resolution (MP4) or as MP3 audio

All network work happens here so the GUI thread can stay responsive.
A progress callback is used to report download progress back to the UI.
"""

import os
import re
import traceback

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

import ffmpeg_utils

_LOG_PATH = os.path.join(os.path.expanduser("~"), "yt_downloader_debug.log")

def _log_error(context, exc):
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n--- {context} ---\n")
            f.write(traceback.format_exc())
    except OSError:
        pass

def is_valid_youtube_url(url):
    if not url or not url.strip():
        return False
    url = url.strip()
    patterns = [
        r"^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^(https?://)?(www\.)?youtu\.be/[\w-]+",
        r"^(https?://)?(www\.)?youtube\.com/shorts/[\w-]+",
        r"^(https?://)?(www\.)?m\.youtube\.com/watch\?v=[\w-]+",
    ]
    return any(re.match(p, url, re.IGNORECASE) for p in patterns)

def _format_size(nbytes):
    if not nbytes:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"

def _format_duration(seconds):
    if not seconds:
        return "N/A"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

_NETWORK_OPT = {
    "socket_timeout": 30,
    "retries": 5,
    "fragment_retries": 5,
}

def extract_video_info(url, progress_callback=None):
    if not is_valid_youtube_url(url):
        raise ValueError("That doesn't look like a valid YouTube URL.")

    if yt_dlp is None:
        raise ImportError("yt-dlp is not installed.")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        **_NETWORK_OPT,
    }

    if progress_callback:
        progress_callback("Fetching video info...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        _log_error("extract_video_info", exc)
        raise Exception(f"Could not fetch video info:\n{exc}")

    title = info.get("title", "Unknown title")
    duration = info.get("duration")
    uploader = info.get("uploader", info.get("channel", "Unknown"))
    
    # Get the best available thumbnail
    thumbnail = info.get("thumbnail", "")
    thumbs = info.get("thumbnails", [])
    if thumbs:
        try:
            best = sorted(thumbs, key=lambda t: t.get("width", 0) or 0, reverse=True)[0]
            thumbnail = best.get("url", thumbnail)
        except Exception:
            pass

    heights = set()
    for fmt in info.get("formats", []):
        height = fmt.get("height")
        vcodec = fmt.get("vcodec")
        if height and vcodec and vcodec != "none":
            heights.add(height)

    sorted_heights = sorted(heights)
    resolution_options = [("Best Available", None)]
    for h in sorted_heights:
        resolution_options.append((f"{h}p", h))

    if len(resolution_options) == 1:
        resolution_options.append(("Best Available (auto)", None))

    if progress_callback:
        progress_callback("Done. Select a resolution and format below.")

    return {
        "title": title,
        "duration": duration,
        "duration_str": _format_duration(duration),
        "uploader": uploader,
        "thumbnail": thumbnail,
        "resolutions": sorted_heights,
        "resolution_options": resolution_options,
        "_raw_info": info,
    }

class DownloadCancelled(Exception):
    pass

class YTDLPDownloader:
    def __init__(self, url, output_dir, format_type="mp4", height=None, mp3_quality="192", raw_info=None):
        self.url = url
        self.output_dir = output_dir
        self.format_type = format_type
        self.height = height
        self.mp3_quality = mp3_quality
        self.raw_info = raw_info
        self._cancel = False

    def cancel(self):
        self._cancel = True

    @property
    def cancelled(self):
        return self._cancel

    def run(self, progress_hook=None, completion_hook=None, ffmpeg_progress_hook=None):
        def _cancel_aware_ffmpeg_cb(downloaded, total):
            if self._cancel:
                raise DownloadCancelled()
            if ffmpeg_progress_hook:
                ffmpeg_progress_hook(downloaded, total)

        try:
            ffmpeg_path = ffmpeg_utils.ensure_ffmpeg(progress_callback=_cancel_aware_ffmpeg_cb)
        except DownloadCancelled:
            if completion_hook: completion_hook(False, "", "Download cancelled by user.")
            return False, "", "Download cancelled by user."
        except RuntimeError as exc:
            _log_error("ensure_ffmpeg", exc)
            if completion_hook: completion_hook(False, "", str(exc))
            return False, "", str(exc)

        if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
            err = "ffmpeg could not be found or downloaded."
            if completion_hook: completion_hook(False, "", err)
            return False, "", err

        os.makedirs(self.output_dir, exist_ok=True)
        outtmpl = os.path.join(self.output_dir, "%(title).80s [%(id)s].%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": os.path.dirname(ffmpeg_path) or ffmpeg_path,
            "concurrent_fragment_downloads": 1,  # SPEED INCREASE
            **_NETWORK_OPT,
        }

        def _cancel_aware_hook(d):
            if self._cancel:
                raise DownloadCancelled()
            if progress_hook:
                progress_hook(d)

        ydl_opts["progress_hooks"] = [_cancel_aware_hook]

        if self.format_type == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": self.mp3_quality,
            }]
        else:
            if self.height:
                ydl_opts["format"] = f"bestvideo[height<={self.height}]+bestaudio/best[height<={self.height}]/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"

        if yt_dlp is None:
            if completion_hook: completion_hook(False, "", "yt-dlp is not installed.")
            return False, "", "yt-dlp is not installed."

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self._cancel: raise DownloadCancelled()
                ydl.download([self.url])

            ext = "mp3" if self.format_type == "mp3" else "mp4"
            output_path = self._find_output_file(ext)

            if completion_hook:
                completion_hook(not self._cancel, output_path, "" if not self._cancel else "Cancelled")
            return not self._cancel, output_path, ""

        except DownloadCancelled:
            if completion_hook: completion_hook(False, "", "Download cancelled by user.")
            return False, "", "Download cancelled by user."
        except Exception as exc:
            _log_error("YTDLPDownloader.run", exc)
            err = f"Download failed:\n{exc}"
            if completion_hook: completion_hook(False, "", err)
            return False, "", err

    def _find_output_file(self, ext):
        try:
            files = [os.path.join(self.output_dir, f) for f in os.listdir(self.output_dir) if f.lower().endswith(f".{ext}")]
            if not files: return ""
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
        except OSError:
            return ""