"""
main.py – YT Downloader  (v2.2.0 – Background, Notifications & Bug Fixes)
"""

import os, sys, threading, queue, urllib.request, uuid, tempfile, json, subprocess, socket
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

try:
    from PIL import Image, ImageTk; _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from downloader import extract_video_info, is_valid_youtube_url, YTDLPDownloader, DownloadCancelled
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
    from downloader import extract_video_info, is_valid_youtube_url, YTDLPDownloader, DownloadCancelled
import ffmpeg_utils

APP_TITLE, APP_VERSION = "YT Downloader", "2.2.0"
THUMB_W, THUMB_H = 280, 158
IPC_PORT = 49876
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".yt_downloader_settings.json")

MP3_QUALITIES = [
    ("Best (320 kbps)", "320"), ("High (256 kbps)", "256"),
    ("Good (192 kbps)", "192"), ("Medium (128 kbps)", "128"),
    ("Low (96 kbps)", "96"),
]

IC = {
    "link": "\uE71B", "paste": "\uE77F", "fetch": "\uE721", "dl": "\uE896",
    "folder": "\uE8B7", "help": "\uE897", "moon": "\uE708", "sun": "\uE706",
    "check": "\uE73E", "cross": "\uE711", "settings": "\uE713",
    "video": "\uE714", "audio": "\uE8D6", "clock": "\uE823",
    "user": "\uE77B", "speed": "\uE7B7", "search": "\uE721",
    "cancel": "\uE711", "info": "\uE946", "trash": "\uE74D", "open": "\uE8E5",
}

LIGHT = dict(
    bg="#F6F8FC", card="#FFFFFF", card_border="#E8EAED",
    primary="#E63946", primary_h="#C5303F", primary_fg="#FFFFFF",
    text="#1F2937", text2="#6B7280", text3="#9CA3AF",
    ok="#10B981", err="#EF4444",
    entry_bg="#F3F4F6", entry_fg="#1F2937", entry_bd="#E5E7EB",
    prog_bg="#E5E7EB", prog_fg="#6C63FF",
    status_bg="#F0F2F5", status_fg="#6B7280",
    btn_bg="#FFFFFF", btn_fg="#374151", btn_hover="#F3F4F6", segmented_bg="#F3F4F6",
)
DARK = dict(
    bg="#0F1117", card="#1A1D2E", card_border="#2A2D3E",
    primary="#7B61FF", primary_h="#6C63FF", primary_fg="#FFFFFF",
    text="#E5E7EB", text2="#9CA3AF", text3="#6B7280",
    ok="#34D399", err="#F87171",
    entry_bg="#252839", entry_fg="#E5E7EB", entry_bd="#363952",
    prog_bg="#2A2D3E", prog_fg="#7B61FF",
    status_bg="#141622", status_fg="#9CA3AF",
    btn_bg="#252839", btn_fg="#D1D5DB", btn_hover="#2F3349", segmented_bg="#252839",
)

FONT = "Segoe UI Variable"

def _default_dir():
    # Use the user's standard Downloads folder as the default
    try:
        d = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(d, exist_ok=True)
        return d
    except:
        # Fallback to current working directory if Downloads isn't available
        return os.getcwd()

def _draw_round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)

class RoundedCard(tk.Canvas):
    def __init__(self, parent, C, padx=24, pady=20, radius=15, **kw):
        super().__init__(parent, bg=C["bg"], highlightthickness=0, **kw)
        self.C, self._padx, self._pady, self._radius = C, padx, pady, radius
        self.rect_id = _draw_round_rect(self, 0, 0, 100, 100, radius, fill=C["card"], outline=C["card_border"])
        self.inner_frame = tk.Frame(self, bg=C["card"])
        self.inner_window = self.create_window(padx, pady, window=self.inner_frame, anchor="nw")
        self.bind("<Configure>", self._on_resize)
        self.inner_frame.bind("<Configure>", self._on_inner_configure)

    @property
    def frame(self): return self.inner_frame

    def _on_inner_configure(self, e=None):
        self.update_idletasks()
        req_h = self.inner_frame.winfo_reqheight() + self._pady * 2 + 6
        if req_h > 1 and abs(self.winfo_reqheight() - req_h) > 2:
            self.configure(height=req_h)

    def _on_resize(self, e):
        w, h = e.width, e.height
        if w < 4 or h < 4: return
        self.delete(self.rect_id)
        self.rect_id = _draw_round_rect(self, 0, 0, w, h, self._radius, fill=self.C["card"], outline=self.C["card_border"])
        self.tag_lower(self.rect_id)
        self.itemconfig(self.inner_window, width=max(w - self._padx * 2, 1))

    def set_theme(self, C):
        self.C = C; self.config(bg=C["bg"]); self.inner_frame.config(bg=C["card"])
        self.itemconfig(self.rect_id, fill=C["card"], outline=C["card_border"])

class RoundedEntry(tk.Canvas):
    def __init__(self, parent, textvariable=None, font=None, bg="#F3F4F6", fg="#1F2937", width=560, height=44, radius=28, **kw):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"), highlightthickness=0)
        self.radius = radius
        self.rect_id = _draw_round_rect(self, 0, 0, width, height, radius, fill=bg, outline="")
        self.entry = tk.Entry(self, textvariable=textvariable, font=font, bd=0, bg=bg, fg=fg, insertbackground=fg, **kw)
        self.create_window(12, height/2, window=self.entry, anchor="w", width=width-24, height=height-12)
    def __getattr__(self, name):
        return getattr(self.entry, name)
    def config(self, cnf=None, **kw):
        if cnf: self.entry.config(cnf)
        if kw: self.entry.config(**kw)
    def bind(self, sequence=None, func=None, add=None):
        self.entry.bind(sequence, func, add)
        return super().bind(sequence, func, add)
    def insert(self, index, string):
        return self.entry.insert(index, string)
    def delete(self, first, last=None):
        if last is None:
            return self.entry.delete(first)
        return self.entry.delete(first, last)
    def get(self):
        return self.entry.get()
    def focus_set(self):
        return self.entry.focus_set()
    def select_range(self, start, end):
        try:
            return self.entry.select_range(start, end)
        except Exception:
            return None

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, C, kind="outlined", icon=None, state="normal", radius=16, padx=24, pady=12, min_width=None):
        self.C, self.kind, self.command, self.state, self.radius = C, kind, command, state, radius
        self.icon = icon
        self.text_str = text
        self.font = (FONT, 10, "bold")
        f = tkfont.Font(font=self.font)
        text_width = f.measure(text)
        icon_width = f.measure(icon) if icon else 0
        spacing = 8 if icon else 0
        self.w = max(text_width + icon_width + spacing + padx * 2, min_width if min_width else 0)
        self.h = f.metrics("linespace") + pady * 2
        super().__init__(parent, width=self.w, height=self.h, bg=parent.cget("bg"), highlightthickness=0)
        self.rect_id = _draw_round_rect(self, 1, 1, self.w-1, self.h-1, radius)
        self.icon_id = None
        if icon:
            x = padx + icon_width / 2
            self.icon_id = self.create_text(x, self.h / 2, text=icon, font=self.font, fill=C["primary"] if kind == "white" else C["primary_fg"])
            self.text_id = self.create_text(x + icon_width / 2 + spacing + text_width / 2, self.h / 2, text=text, font=self.font, fill=C["text"] if kind == "white" else C["primary_fg"])
        else:
            self.text_id = self.create_text(self.w / 2, self.h / 2, text=text, font=self.font, fill=C["primary_fg"])
        self.bind("<Enter>", self._on_enter); self.bind("<Leave>", self._on_leave); self.bind("<Button-1>", self._on_click)
        self.update_theme(C)

    def _set_normal(self):
        if self.state == "disabled":
            self.itemconfig(self.rect_id, fill=self.C["card_border"], outline=self.C["card_border"])
            if self.icon_id: self.itemconfig(self.icon_id, fill=self.C["text3"])
            self.itemconfig(self.text_id, fill=self.C["text3"])
        else:
            if self.kind == "primary" or self.kind == "red":
                self.itemconfig(self.rect_id, fill=self.C["primary"], outline=self.C["primary"])
                if self.icon_id: self.itemconfig(self.icon_id, fill=self.C["primary_fg"])
                self.itemconfig(self.text_id, fill=self.C["primary_fg"])
            elif self.kind == "white":
                self.itemconfig(self.rect_id, fill=self.C["primary_fg"], outline=self.C["card_border"])
                if self.icon_id: self.itemconfig(self.icon_id, fill=self.C["primary"])
                self.itemconfig(self.text_id, fill=self.C["text"])
            elif self.kind == "outlined":
                self.itemconfig(self.rect_id, fill=self.C["entry_bg"], outline=self.C["card_border"])
                if self.icon_id: self.itemconfig(self.icon_id, fill=self.C["btn_fg"])
                self.itemconfig(self.text_id, fill=self.C["btn_fg"])
            else:
                self.itemconfig(self.rect_id, fill=self.C["card"], outline=self.C["card"])
                if self.icon_id: self.itemconfig(self.icon_id, fill=self.C["btn_fg"])
                self.itemconfig(self.text_id, fill=self.C["btn_fg"])

    def update_theme(self, C): self.C = C; self._set_normal()
    def set_colors(self, bg, fg, outline=""): self.itemconfig(self.rect_id, fill=bg, outline=outline if outline else bg); self.itemconfig(self.text_id, fill=fg)
    def _on_enter(self, e):
        if self.state != "normal":
            return
        if self.kind == "primary" or self.kind == "red":
            self.itemconfig(self.rect_id, fill=self.C["primary_h"], outline=self.C["primary_h"])
        elif self.kind == "white":
            self.itemconfig(self.rect_id, fill=self.C["btn_hover"], outline=self.C["card_border"])
        else:
            self.itemconfig(self.rect_id, fill=self.C["btn_hover"], outline=self.C["btn_hover"])
        self.config(cursor="hand2")
    def _on_leave(self, e):
        self._set_normal()
        self.config(cursor="")
    def _on_click(self, e):
        if self.state == "normal" and self.command: self.command()
    def config(self, **kw):
        if "state" in kw: self.state = kw["state"]; self._set_normal()
        if "text" in kw: self.text_str = kw["text"]; self.itemconfig(self.text_id, text=self.text_str)
        if "command" in kw: self.command = kw["command"]
        if "fg" in kw: self.itemconfig(self.text_id, fill=kw["fg"])

class _PBar(tk.Canvas):
    def __init__(self, parent, h=14, C=None, **kw):
        super().__init__(parent, height=h, highlightthickness=0, bd=0, bg=C["prog_bg"] if C else "#E5E7EB")
        self.C = C; self._v, self._mx = 0.0, 100.0; self._ind, self._off, self._aid = False, 0.0, None; self._done, self._done_ok = False, False
        self.bind("<Configure>", lambda e: self._draw())
    def set(self, v): self._ind = False; self._done = False; self._stop(); self._v = min(max(v, 0), self._mx); self._draw()
    def set_done(self, ok=True): self._ind = False; self._done = True; self._done_ok = ok; self._stop(); self._v = 100 if ok else 0; self._draw()
    def start_ind(self):
        if self._ind: return
        self._ind = True; self._done = False; self._off = 0.0; self._run()
    def stop(self): self._ind = False; self._stop(); self._draw()
    def _stop(self):
        if self._aid:
            try: self.after_cancel(self._aid)
            except: pass
            self._aid = None
    def _run(self):
        if not self._ind or not self.winfo_exists(): return
        self._off = (self._off + 4.0) % 200; self._draw(); self._aid = self.after(40, self._run)
    def _draw(self):
        self.delete("all"); w, h = self.winfo_width(), self.winfo_height()
        if w < 2: return
        C = self.C; bg = C["prog_bg"] if C else "#E5E7EB"
        fg = C["ok"] if self._done and self._done_ok else C["err"] if self._done else C["prog_fg"] if C else "#6C63FF"
        _draw_round_rect(self, 0, 0, w, h, h//2, fill=bg, outline="")
        if self._ind:
            bw = max(w * 0.25, 28); x = (self._off / 200) * (w + bw) - bw; x2 = min(x + bw, w); x = max(x, 0)
            if x2 > x: _draw_round_rect(self, x, 0, x2, h, h//2, fill=fg, outline="")
        elif self._v > 0:
            fw = max(int(self._v / self._mx * w), 1)
            if fw == w: _draw_round_rect(self, 0, 0, fw, h, h//2, fill=fg, outline="")
            else: self.create_rectangle(0, 0, fw, h, fill=fg, outline="")
    def recolor(self, C): self.C = C; self.config(bg=C["prog_bg"]); self._draw()

class YTDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1280x850"); self.root.minsize(900, 700); self.root.resizable(True, True)
        self._dark = False; self.C = LIGHT
        self.video_info = None; self._downloads = {}; self._thumb_image = None; self.workers = []
        self._url_var = tk.StringVar(); self._format_var = tk.StringVar(value="mp4")
        self._output_dir_var = tk.StringVar(value=_default_dir()); self._resolution_var = tk.StringVar()
        self._mp3_quality_var = tk.StringVar(); self._status_var = tk.StringVar(value="Ready  •  Paste a YouTube URL")
        self._msg_queue = queue.Queue(); self._url_ph = False; self._cards = []; self._pbars = []; self._tkbtns = []
        self._is_background = False
        self._settings = self._load_settings()
        self._build_ui(); self._poll_queue()

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        except: return {"sound_on_finish": True, "notifications": True, "background_download": True}

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f: json.dump(self._settings, f)
        except: pass

    def _apply_theme(self):
        C = self.C
        self.root.config(bg=C["bg"]); self._body.config(bg=C["bg"]); self._scroll.config(bg=C["bg"]); self._pad.config(bg=C["bg"])
        for c in self._cards: c.set_theme(C)
        for p in self._pbars: p.recolor(C)
        for b in self._tkbtns: b.update_theme(C)
        for attr in ("url_entry", "folder_entry"):
            w = getattr(self, attr, None)
            if w: w.config(bg=C["entry_bg"], fg=C["entry_fg"], insertbackground=C["entry_fg"], highlightbackground=C["entry_bd"])
        for attr in ("_hdr_title", "_hdr_sub", "_hdr_ver", "_info_title", "_info_sub", "_opt_fmt_lbl", "_opt_q_lbl", "_opt_save_lbl"):
            w = getattr(self, attr, None)
            if w: w.config(bg=C["card"], fg=C["text"] if "title" in attr else C["text2"])
        self._update_seg()
        if hasattr(self, "_sbar"): self._sbar.config(bg=C["status_bg"])
        for attr in ("_sdot", "_stxt", "_sver"):
            w = getattr(self, attr, None)
            if w: w.config(bg=C["status_bg"])
        if hasattr(self, "_sdot"): self._sdot.config(fg=C["ok"])
        if hasattr(self, "_stxt"): self._stxt.config(fg=C["status_fg"])
        if hasattr(self, "_sver"): self._sver.config(fg=C["text3"])
        if hasattr(self, "_thumb"): self._thumb.config(bg=C["entry_bg"], fg=C["text3"], highlightbackground=C["card_border"])
        if hasattr(self, "_dl_count"): self._dl_count.config(bg=C["card"], fg=C["text3"])
        for dl in self._downloads.values():
            for lbl_attr in ("title_lbl", "meta_lbl", "status_lbl"):
                w = dl.get(lbl_attr)
                if w: w.config(bg=C["card"]); w.config(fg=C["text"] if lbl_attr == "title_lbl" else C["text2"])
            if "thumb" in dl: dl["thumb"].config(bg=C["entry_bg"], fg=C["text3"], highlightbackground=C["card_border"])
            if "fmt_badge" in dl: dl["fmt_badge"].config(bg=C["primary"], fg=C["primary_fg"])
        if hasattr(self, "_dark_btn"): self._dark_btn.config(text=f"  {IC['sun'] if self._dark else IC['moon']}  ")
        self._style_ttk()

    def _style_ttk(self):
        C = self.C; style = ttk.Style()
        try:
            style.theme_use("clam")
            style.configure("YT.TCombobox", fieldbackground=C["entry_bg"], background=C["entry_bg"], foreground=C["entry_fg"], bordercolor=C["entry_bd"], lightcolor=C["entry_bd"], darkcolor=C["entry_bd"], arrowcolor=C["text2"], padding=10, relief="flat")
            style.map("YT.TCombobox", fieldbackground=[("readonly", C["entry_bg"])], foreground=[("readonly", C["entry_fg"])], background=[("readonly", C["entry_bg"])], bordercolor=[("focus", C["primary"])])
            style.configure("YT.Vertical.TScrollbar", background=C["card"], troughcolor=C["bg"], bordercolor=C["bg"], arrowcolor=C["text2"], relief="flat", borderwidth=0, arrowsize=14)
            style.map("YT.Vertical.TScrollbar", background=[("active", C["btn_hover"])])
            self.root.option_add('*TCombobox*Listbox.background', C['entry_bg']); self.root.option_add('*TCombobox*Listbox.foreground', C['entry_fg'])
            self.root.option_add('*TCombobox*Listbox.selectBackground', C['primary']); self.root.option_add('*TCombobox*Listbox.selectForeground', C['primary_fg'])
        except: pass

    def _btn(self, parent, text, cmd, kind="outlined", icon=None, state="normal", min_width=None):
        b = RoundedButton(parent, text, cmd, self.C, kind=kind, icon=icon, state=state, min_width=min_width); self._tkbtns.append(b); return b

    def _build_ui(self):
        self._body = tk.Frame(self.root, bg=self.C["bg"]); self._body.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(self._body, bg=self.C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(self._body, orient=tk.VERTICAL, command=canvas.yview, style="YT.Vertical.TScrollbar")
        self._scroll = tk.Frame(canvas, bg=self.C["bg"])
        self._scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._scroll_win = canvas.create_window((0, 0), window=self._scroll, anchor=tk.NW)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._scroll_win, width=e.width))
        canvas.configure(yscrollcommand=sb.set); canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)
        self._main_canvas = canvas

        self._pad = tk.Frame(self._scroll, bg=self.C["bg"]); self._pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)
        self._build_top_panel();
        self._mid_row = tk.Frame(self._pad, bg=self.C["bg"])
        self._mid_row.pack(fill=tk.BOTH, expand=True, pady=(0, 16))
        self._left_col = tk.Frame(self._mid_row, bg=self.C["bg"]); self._left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        self._right_col = tk.Frame(self._mid_row, bg=self.C["bg"]); self._right_col.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        self._build_info_section(); self._build_downloads_section(); self._build_options_section(); self._build_action_buttons(); self._build_status_bar(); self._apply_theme()

    def _build_header(self):
        C = self.C; card = RoundedCard(self._pad, C); card.pack(fill=tk.X, expand=True, pady=(0, 16)); self._cards.append(card); f = card.frame
        top = tk.Frame(f, bg=C["card"]); top.pack(fill=tk.X, expand=True)
        left = tk.Frame(top, bg=C["card"]); left.pack(side=tk.LEFT)
        logo = tk.Canvas(left, width=56, height=56, bg=C["card"], highlightthickness=0); logo.pack(side=tk.LEFT, padx=(0, 14))
        _draw_round_rect(logo, 0, 0, 56, 56, 12, fill=C["primary"], outline=""); logo.create_polygon(20, 14, 20, 42, 42, 28, fill="white", outline="")
        self._hdr_title = tk.Label(left, text=APP_TITLE, font=(FONT, 28, "bold"), bg=C["card"], fg=C["text"]); self._hdr_title.pack(side=tk.LEFT, padx=(0, 8))
        self._hdr_ver = tk.Label(left, text=f"v{APP_VERSION}", font=(FONT, 11), bg=C["card"], fg=C["text3"]); self._hdr_ver.pack(side=tk.LEFT, anchor="s", pady=(0, 8))
        right = tk.Frame(top, bg=C["card"]); right.pack(side=tk.RIGHT)
        self._settings_btn = self._btn(right, "Settings", self._open_settings, "ghost", IC["settings"]); self._settings_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._help_btn = self._btn(right, "Help", self._on_help, "ghost", IC["help"]); self._help_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._dark_btn = self._btn(right, "", self._toggle_dark, "ghost", IC["moon"]); self._dark_btn.pack(side=tk.LEFT)
        self._hdr_sub = tk.Label(f, text="Download YouTube videos as MP4 or MP3 — No API required.", font=(FONT, 11), bg=C["card"], fg=C["text2"]); self._hdr_sub.pack(anchor=tk.W, pady=(12, 0))

    def _build_url_section(self):
        C = self.C; card = RoundedCard(self._pad, C); card.pack(fill=tk.X, expand=True, pady=(0, 16)); self._cards.append(card); f = card.frame
        tk.Label(f, text=f'{IC["link"]}  Video URL', font=(FONT, 12, "bold"), bg=C["card"], fg=C["text"]).pack(anchor=tk.W, pady=(0, 12))
        row = tk.Frame(f, bg=C["card"]); row.pack(fill=tk.X, expand=True)
        self.url_entry = tk.Entry(row, textvariable=self._url_var, font=(FONT, 12), relief="flat", bd=0, bg=C["entry_bg"], fg=C["entry_fg"], insertbackground=C["entry_fg"], highlightbackground=C["entry_bd"], highlightthickness=2)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12), ipady=14)
        self.url_entry.bind("<Return>", lambda e: self._on_fetch()); self.url_entry.bind("<FocusIn>", self._url_fi); self.url_entry.bind("<FocusOut>", self._url_fo); self._url_ph_show()
        self._paste_btn = self._btn(row, "Paste", self._on_paste, "outlined", IC["paste"]); self._paste_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._fetch_btn = self._btn(row, "Fetch", self._on_fetch, "primary", IC["search"]); self._fetch_btn.pack(side=tk.LEFT)

    def _url_ph_show(self):
        if not self._url_var.get():
            self._url_ph = True
            w = self.url_entry.entry if hasattr(self.url_entry, "entry") else self.url_entry
            w.config(fg=self.C["text3"])
            try:
                w.delete(0, tk.END)
            except Exception:
                pass
            try:
                w.insert(0, "  Paste YouTube URL here...")
            except Exception:
                pass
    def _url_fi(self, e=None):
        if self._url_ph:
            w = self.url_entry.entry if hasattr(self.url_entry, "entry") else self.url_entry
            try:
                w.delete(0, tk.END)
            except Exception:
                pass
            w.config(fg=self.C["entry_fg"]); self._url_ph = False
    def _url_fo(self, e=None):
        w = self.url_entry.entry if hasattr(self.url_entry, "entry") else self.url_entry
        try:
            if not w.get().strip(): self._url_ph_show()
        except Exception:
            pass

    def _build_top_panel(self):
        C = self.C; card = RoundedCard(self._pad, C); card.pack(fill=tk.X, expand=True, pady=(0, 16)); self._cards.append(card); f = card.frame
        top = tk.Frame(f, bg=C["card"]); top.pack(fill=tk.X, expand=True, pady=(12, 6))
        logo = tk.Canvas(top, width=44, height=44, bg=C["card"], highlightthickness=0)
        logo.pack(side=tk.LEFT, padx=(0, 10))
        logo.create_oval(2, 2, 42, 42, fill="#FF0000", outline="")
        logo.create_polygon(18, 14, 18, 30, 32, 22, fill="#FFFFFF", outline="")
        self._hdr_title = tk.Label(top, text=APP_TITLE, font=(FONT, 32, "bold"), bg=C["card"], fg=C["text"])
        self._hdr_title.pack(side=tk.LEFT, padx=(0, 8))
        self._hdr_sub = tk.Label(f, text="Download YouTube videos as MP4 or MP3 — no API key needed", font=(FONT, 11), bg=C["card"], fg=C["text2"])
        self._hdr_sub.pack(anchor=tk.W, pady=(0, 6))
        row = tk.Frame(f, bg=C["card"])
        row.pack(fill=tk.X, expand=True, pady=(0, 2))
        self.url_entry = RoundedEntry(row, textvariable=self._url_var, font=(FONT, 12), bg=C["entry_bg"], fg=C["entry_fg"], height=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.url_entry.bind("<Return>", lambda e: self._on_fetch()); self.url_entry.bind("<FocusIn>", self._url_fi); self.url_entry.bind("<FocusOut>", self._url_fo); self._url_ph_show()
        btn_row = tk.Frame(row, bg=C["card"])
        btn_row.pack(side=tk.LEFT)
        self._paste_btn = self._btn(btn_row, "Paste", self._on_paste, "white", IC["paste"], min_width=112)
        self._paste_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._fetch_btn = self._btn(btn_row, "Fetch", self._on_fetch, "red", IC["search"], min_width=112)
        self._fetch_btn.pack(side=tk.LEFT)

    def _build_info_section(self):
        C = self.C; card = RoundedCard(self._left_col, C); card.pack(fill=tk.BOTH, expand=True, pady=(0, 16)); self._cards.append(card); f = card.frame
        tk.Label(f, text=f'{IC["video"]}  Video Information', font=(FONT, 12, "bold"), bg=C["card"], fg=C["text"]).pack(anchor=tk.W, pady=(0, 12))
        row = tk.Frame(f, bg=C["card"]); row.pack(fill=tk.BOTH, expand=True)
        self._thumb = tk.Label(row, text=f"\n{IC['info']}\nNo Preview", font=(FONT, 12), bg=C["entry_bg"], fg=C["text3"], relief="flat", width=34, height=11, highlightbackground=C["card_border"], highlightthickness=1)
        self._thumb.pack(side=tk.LEFT, padx=(0, 24), pady=(0, 4))
        col = tk.Frame(row, bg=C["card"]); col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._info_title = tk.Label(col, text="—", font=(FONT, 18, "bold"), bg=C["card"], fg=C["text"], anchor="nw", justify="left", wraplength=520); self._info_title.pack(fill=tk.X, pady=(0, 6))
        self._info_sub = tk.Label(col, text="Duration: —\nChannel: —", font=(FONT, 10), bg=C["card"], fg=C["text2"], anchor="nw", justify="left", wraplength=520); self._info_sub.pack(fill=tk.X)

    def _build_options_section(self):
        C = self.C; card = RoundedCard(self._right_col, C); card.pack(fill=tk.X, expand=False, pady=(0, 16)); self._cards.append(card); f = card.frame
        tk.Label(f, text=f'{IC["dl"]}  Download Options', font=(FONT, 12, "bold"), bg=C["card"], fg=C["text"]).pack(anchor=tk.W, pady=(0, 14))
        self._seg_frame = tk.Frame(f, bg=C["card"]); self._seg_frame.pack(fill=tk.X, pady=(0, 18))
        self._build_seg()
        tk.Label(f, text="Quality", font=(FONT, 10, "bold"), bg=C["card"], fg=C["text"]).pack(anchor=tk.W)
        self._res_combo = ttk.Combobox(f, textvariable=self._resolution_var, state="readonly", width=24, font=(FONT, 10), style="YT.TCombobox")
        self._res_combo.pack(fill=tk.X, pady=(6, 16))
        tk.Label(f, text="Save Location", font=(FONT, 10, "bold"), bg=C["card"], fg=C["text"]).pack(anchor=tk.W)
        s_row = tk.Frame(f, bg=C["card"]); s_row.pack(fill=tk.X, pady=(6, 18))
        self.folder_entry = tk.Entry(s_row, textvariable=self._output_dir_var, state="readonly", font=(FONT, 10), relief="flat", bd=0, bg=C["entry_bg"], fg=C["entry_fg"], highlightbackground=C["entry_bd"], highlightthickness=1)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        self._browse_btn = self._btn(s_row, "Browse", self._on_browse, "outlined", IC["folder"]); self._browse_btn.pack(side=tk.RIGHT)
        self._mp3_combo = ttk.Combobox(f, textvariable=self._mp3_quality_var, state="readonly", width=24, font=(FONT, 10), style="YT.TCombobox")
        self._mp3_combo["values"] = [l for l, _ in MP3_QUALITIES]
        if MP3_QUALITIES: self._mp3_combo.current(2)
        self._opt_w = [self._res_combo, self._mp3_combo]; self._set_opts("disabled")
        self._action_frame = tk.Frame(f, bg=C["card"]); self._action_frame.pack(fill=tk.X, pady=(14, 0))
        self._dl_btn = self._btn(self._action_frame, "Download", self._on_download, "red", IC["dl"], "disabled", min_width=150); self._dl_btn.pack(side=tk.LEFT)
        self._cancel_btn = self._btn(self._action_frame, "Cancel All", self._on_cancel, "outlined", IC["cancel"], "disabled", min_width=150); self._cancel_btn.pack(side=tk.LEFT, padx=(10, 0))

    def _build_seg(self):
        C = self.C
        for w in self._seg_frame.winfo_children(): w.destroy()
        bg = tk.Frame(self._seg_frame, bg=C["segmented_bg"], padx=3, pady=3, highlightbackground=C["card_border"], highlightthickness=1); bg.pack(side=tk.LEFT)
        self._seg_a = self._btn(bg, f"{IC['video']} MP4", lambda: self._set_fmt("mp4"), "ghost"); self._seg_a.pack(side=tk.LEFT, padx=1, pady=1)
        self._seg_b = self._btn(bg, f"{IC['audio']} MP3", lambda: self._set_fmt("mp3"), "ghost"); self._seg_b.pack(side=tk.LEFT, padx=1, pady=1)
        self._update_seg()

    def _update_seg(self):
        C = self.C; fmt = self._format_var.get()
        for b, v in ((self._seg_a, "mp4"), (self._seg_b, "mp3")):
            if v == fmt: b.set_colors(C["primary"], C["primary_fg"], outline=C["primary"])
            else: b.set_colors(C["segmented_bg"], C["text2"], outline=C["segmented_bg"])

    def _set_fmt(self, v): self._format_var.set(v); self._update_seg(); self._on_fmt_change()

    def _build_downloads_section(self):
        C = self.C; card = RoundedCard(self._left_col, C); card.pack(fill=tk.BOTH, expand=True, pady=(0, 16)); self._cards.append(card); self._dl_card = card; f = card.frame
        hdr = tk.Frame(f, bg=C["card"]); hdr.pack(fill=tk.X, expand=True, pady=(0, 12))
        self._dl_toggle = tk.Frame(hdr, bg=C["card"]); self._dl_toggle.pack(side=tk.LEFT)
        self._dl_expand_icon = tk.Label(self._dl_toggle, text="▶", font=(FONT, 10, "bold"), bg=C["card"], fg=C["text2"])
        self._dl_expand_icon.pack(side=tk.LEFT)
        self._dl_header = tk.Label(self._dl_toggle, text=f'  {IC["dl"]}  Downloads list', font=(FONT, 12, "bold"), bg=C["card"], fg=C["text"])
        self._dl_header.pack(side=tk.LEFT)
        self._dl_header.bind("<Button-1>", lambda e: self._toggle_downloads())
        self._dl_expand_icon.bind("<Button-1>", lambda e: self._toggle_downloads())
        self._dl_count = tk.Label(hdr, text="", font=(FONT, 10), bg=C["card"], fg=C["text3"]); self._dl_count.pack(side=tk.RIGHT)
        self._dl_panel = tk.Frame(f, bg=C["card"])
        self._dl_panel.pack(fill=tk.BOTH, expand=True)
        self._dl_canvas = tk.Canvas(self._dl_panel, height=160, highlightthickness=0, bd=0, bg=C["card"])
        self._dl_sb = ttk.Scrollbar(self._dl_panel, orient=tk.VERTICAL, command=self._dl_canvas.yview, style="YT.Vertical.TScrollbar")
        self._dl_canvas.configure(yscrollcommand=self._dl_sb.set); self._dl_sb.pack(side=tk.RIGHT, fill=tk.Y); self._dl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._dl_inner = tk.Frame(self._dl_canvas, bg=C["card"]); self._dl_cw = self._dl_canvas.create_window((0, 0), window=self._dl_inner, anchor=tk.NW)
        self._dl_inner.bind("<Configure>", lambda e: self._dl_canvas.configure(scrollregion=self._dl_canvas.bbox("all")))
        self._dl_canvas.bind("<Configure>", lambda e: self._dl_canvas.itemconfig(self._dl_cw, width=e.width))
        self._dl_ph = tk.Label(self._dl_inner, text=f"\n{IC['dl']}\n\nNo active downloads\n\nFetch a video and click Download to get started", font=(FONT, 11), bg=C["card"], fg=C["text3"], justify="center")
        self._dl_ph.pack(pady=24, fill=tk.X, expand=True)
        self._downloads_collapsed = False

    def _build_action_buttons(self):
        bf = tk.Frame(self._right_col, bg=self.C["bg"]); bf.pack(fill=tk.X, expand=False, pady=(0, 0))
        # Buttons now built inside options panel; keep fallback support if missing
        if not hasattr(self, '_dl_btn'):
            self._dl_btn = self._btn(bf, "Download", self._on_download, "red", IC["dl"], "disabled", min_width=240); self._dl_btn.pack(side=tk.LEFT)
            self._cancel_btn = self._btn(bf, "Cancel All", self._on_cancel, "outlined", IC["cancel"], "disabled"); self._cancel_btn.pack(side=tk.LEFT, padx=(14, 0))
            self._clear_btn = self._btn(bf, "Clear", self._on_clear, "outlined", IC["trash"], "disabled"); self._clear_btn.pack(side=tk.LEFT, padx=(14, 0))

    def _build_status_bar(self):
        C = self.C; self._sbar = tk.Frame(self.root, bg=C["status_bg"], padx=20, pady=8); self._sbar.pack(fill=tk.X, side=tk.BOTTOM)
        left = tk.Frame(self._sbar, bg=C["status_bg"]); left.pack(side=tk.LEFT)
        self._sdot = tk.Label(left, text="●", font=(FONT, 9), bg=C["status_bg"], fg=C["ok"]); self._sdot.pack(side=tk.LEFT, padx=(0, 10))
        self._stxt = tk.Label(left, textvariable=self._status_var, font=(FONT, 10), bg=C["status_bg"], fg=C["status_fg"]); self._stxt.pack(side=tk.LEFT)
        self._sver = tk.Label(self._sbar, text=f"{APP_TITLE} v{APP_VERSION}", font=(FONT, 9), bg=C["status_bg"], fg=C["text3"]); self._sver.pack(side=tk.RIGHT)

    def _poll_queue(self):
        try:
            while True:
                t, *a = self._msg_queue.get_nowait(); self._handle(t, *a)
        except queue.Empty: pass
        self.root.after(50, self._poll_queue)

    def _is_descendant(self, widget, ancestor):
        while widget:
            if widget is ancestor: return True
            widget = getattr(widget, "master", None)
        return False

    def _on_mousewheel(self, event):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = int(-1 * (event.delta / 120))
        elif getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        if not delta:
            return
        widget = event.widget
        if self._is_descendant(widget, self._dl_canvas):
            self._dl_canvas.yview_scroll(delta, "units")
        elif self._is_descendant(widget, self._main_canvas) or self._is_descendant(widget, self._pad):
            self._main_canvas.yview_scroll(delta, "units")

    def _handle(self, t, *a):
        if t == "status": self._status_var.set(a[0])
        elif t == "info": self._show_info(a[0])
        elif t == "error": self._idle(); messagebox.showerror("Error", a[0])
        elif t == "ffmpeg_progress": self._upd_row(a[0], pct=a[1], text=f"Converting… {a[1]:.0f}%")
        elif t == "dl_progress": self._upd_row(a[0], pct=a[1], text=a[2])
        elif t == "download_done": self._fin_row(a[0], a[1], a[2], a[3])

    def _send(self, t, *a): self._msg_queue.put((t, *a))

    def _idle(self):
        self._fetch_btn.config(state="normal")
        if self.video_info: self._dl_btn.config(state="normal")
        self._upd_cancel(); self._upd_clear(); self._set_opts("normal")
        n = sum(1 for d in self._downloads.values() if d.get("active"))
        self._status_var.set(f"{n} download(s) active" if n else "Ready  •  Paste a YouTube URL")
        self._sdot.config(fg=self.C["ok"]); self.root.config(cursor="")

    def _busy(self, m):
        self._fetch_btn.config(state="disabled"); self._dl_btn.config(state="disabled")
        self._set_opts("disabled"); self._status_var.set(m)
        self._sdot.config(fg=self.C["primary"]); self.root.config(cursor="watch")

    def _upd_cancel(self):
        ok = any(d.get("active") for d in self._downloads.values())
        self._cancel_btn.config(state="normal" if ok else "disabled")

    def _upd_clear(self):
        has_done = any(not d.get("active") for d in self._downloads.values())
        self._clear_btn.config(state="normal" if has_done else "disabled")

    def _set_opts(self, s):
        for w in self._opt_w:
            if w is self._res_combo:
                if self._format_var.get() == "mp3": w.config(state="disabled")
                else: w.config(state="readonly" if (s == "normal" and self.video_info) else "disabled")
            elif w is self._mp3_combo:
                if self._format_var.get() == "mp3": w.config(state="readonly" if s == "normal" else "disabled")
                else: w.config(state="disabled")

    def _show_info(self, info):
        self.video_info = info
        self._info_title.config(text=info["title"])
        p = []
        if info.get("duration_str"): p.append(f'{IC["clock"]}  {info["duration_str"]}')
        if info.get("uploader"): p.append(f'{IC["user"]}  {info["uploader"]}')
        self._info_sub.config(text="     ".join(p) if p else "")
        self._load_thumb(info.get("thumbnail", ""))
        labels = [l for l, _ in info["resolution_options"]]
        self._res_combo["values"] = labels
        if labels: self._res_combo.current(0)
        self._set_opts("normal"); self._dl_btn.config(state="normal")
        self._fetch_btn.config(state="normal")
        self.root.config(cursor=""); self._status_var.set("Ready  •  Choose options and Download")

    def _load_thumb(self, url):
        if not url: self._thumb_ph(); return
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://www.youtube.com/"
            })
            data = urllib.request.urlopen(req, timeout=15).read()
            photo = self._to_photo(data)
            if photo:
                self._thumb_image = photo
                self._thumb.config(image=self._thumb_image, text="", width=THUMB_W, height=THUMB_H)
            else: self._thumb_ph()
        except: self._thumb_ph()

    def _to_photo(self, data):
        if _HAS_PIL:
            from io import BytesIO
            return ImageTk.PhotoImage(Image.open(BytesIO(data)).resize((THUMB_W, THUMB_H), Image.LANCZOS))
        if os.name == "nt": return self._gdip(data)
        return None

    def _gdip(self, data):
        import ctypes; from ctypes import Structure
        try:
            g = ctypes.windll.gdiplus
            class S(Structure): _fields_ = [("V",ctypes.c_uint),("D",ctypes.c_void_p),("S",ctypes.c_int),("E",ctypes.c_int)]
            class G(Structure): _fields_ = [("D1",ctypes.c_ulong),("D2",ctypes.c_ushort),("D3",ctypes.c_ushort),("D4",ctypes.c_byte*8)]
            tk_ = ctypes.c_ulonglong(0); si = S(1,None,0,0); g.GdiplusStartup(ctypes.byref(tk_), ctypes.byref(si), None)
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False); tmp.write(data); tmp.close()
            ip = ctypes.c_void_p()
            if g.GdipLoadImageFromFile(ctypes.c_wchar_p(tmp.name), ctypes.byref(ip)) != 0: os.unlink(tmp.name); return None
            bp = ctypes.c_void_p(); gp = ctypes.c_void_p()
            g.GdipCreateBitmapFromScan0(THUMB_W,THUMB_H,0,0x26200A,None,ctypes.byref(bp)); g.GdipGetImageGraphicsContext(bp, ctypes.byref(gp))
            g.GdipSetInterpolationMode(gp, 7); g.GdipDrawImageRectI(gp, ip, 0, 0, THUMB_W, THUMB_H)
            bpath = tmp.name.replace(".jpg", ".bmp"); cl = G(0xb96b3cab,0x0728,0x11d3,(ctypes.c_byte*8)(0x9d,0x8b,0x00,0xc0,0x4f,0xd9,0x18,0x94))
            g.GdipSaveImageToFile(bp, ctypes.c_wchar_p(bpath), ctypes.byref(cl), None)
            g.GdipDisposeImage(ip); g.GdipDeleteGraphics(gp); g.GdipDisposeImage(bp); os.unlink(tmp.name)
            p = tk.PhotoImage(file=bpath); os.unlink(bpath); return p
        except: return None

    def _thumb_ph(self):
        self._thumb_image = None
        self._thumb.config(text=f"\n{IC['info']}\nNo Preview", image="", width=32, height=9)

    def _on_paste(self, e=None):
        try:
            t = self.root.clipboard_get()
            if t:
                w = self.url_entry.entry if hasattr(self.url_entry, "entry") else self.url_entry
                try:
                    w.delete(0, tk.END)
                except Exception:
                    pass
                try:
                    w.insert(0, t.strip())
                except Exception:
                    pass
                self._url_ph = False; w.config(fg=self.C["entry_fg"])
        except: pass

    def _on_fetch(self):
        if yt_dlp is None: messagebox.showerror("Missing", "yt-dlp is not installed.\npip install yt-dlp"); return
        url = self._url_var.get().strip()
        if not url: messagebox.showwarning("No URL", "Please paste a YouTube URL first."); return
        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "That doesn't look like a YouTube URL.\n\nValid: https://www.youtube.com/watch?v=...\n       https://youtu.be/..."); return
        self.video_info = None; self._thumb_ph(); self._busy("Fetching video info…")
        t = threading.Thread(target=self._w_fetch, args=(url,), daemon=True); t.start(); self.workers.append(t)

    def _w_fetch(self, url):
        try:
            info = extract_video_info(url, progress_callback=lambda m: self._send("status", m))
            self._send("info", info); self._send("status", "Ready  •  Choose options and Download")
        except Exception as e: self._send("error", str(e))

    def _on_download(self):
        if not self.video_info: messagebox.showwarning("No video", "Please fetch a video URL first."); return
        url = self._url_var.get().strip(); od = self._output_dir_var.get().strip(); fmt = self._format_var.get()
        if not od or not os.path.isdir(od): messagebox.showerror("Invalid folder", "Please choose a valid output folder."); return
        h = None
        for l, hv in self.video_info["resolution_options"]:
            if l == self._resolution_var.get(): h = hv; break
        mq = "192"
        for l, b in MP3_QUALITIES:
            if l == self._mp3_quality_var.get(): mq = b; break
        did = str(uuid.uuid4())[:8]; title = self.video_info.get("title", "Unknown")
        self._mk_row(did, title); self._url_var.set(""); self._url_ph = False; self._url_fo()
        dl = YTDLPDownloader(url=url, output_dir=od, format_type=fmt, height=h, mp3_quality=mq, raw_info=self.video_info.get("_raw_info"))
        self._downloads[did].update({ "downloader": dl, "active": True, "title": title })
        self._upd_cancel()
        t = threading.Thread(target=self._w_dl, args=(did, dl), daemon=True); t.start(); self.workers.append(t)
        self._status_var.set(f"Downloading: {title}"); self._update_dl_count()

    def _w_dl(self, did, dl):
        def ffp(d, t):
            try:
                if t: self._send("ffmpeg_progress", did, d / t * 100)
            except: pass

        def ph(d):
            try:
                if d["status"] == "downloading":
                    tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    dn = d.get("downloaded_bytes", 0); sp = d.get("speed")
                    def _fmt_bytes(b):
                        if not b: return "0.0MB"
                        mb = b / (1024 * 1024)
                        if mb < 1: return f"{b/1024:.1f}KB"
                        return f"{mb:.1f}MB"
                    if tot:
                        pct = dn / tot * 100
                        # BUG FIX: Combine Video and Audio progress smoothly
                        overall_pct = pct
                        if self._format_var.get() == "mp4":
                            stream_num = self._downloads[did].get("stream_num", 1)
                            if pct < self._downloads[did].get("last_pct", 101):
                                stream_num += 1
                                self._downloads[did]["stream_num"] = stream_num
                            self._downloads[did]["last_pct"] = pct
                            if stream_num == 1: overall_pct = pct * 0.8
                            else: overall_pct = 80 + (pct * 0.2)
                            overall_pct = min(99, overall_pct)
                            
                        txt = f"{overall_pct:.0f}% Complete     {_fmt_bytes(dn)} / {_fmt_bytes(tot)}     {_fmt_bytes(sp)}/s"
                        self._send("dl_progress", did, overall_pct, txt)
                    else:
                        mb = dn / 1024 / 1024; pct = min(95, max(5, mb * 3))
                        txt = f"{pct:.0f}% Complete     {_fmt_bytes(dn)}     {_fmt_bytes(sp)}/s"
                        self._send("dl_progress", did, pct, txt)
                elif d["status"] == "finished":
                    self._send("dl_progress", did, 100, "Processing...")
                    self._send("status", "Processing media... this may take a moment.")
            except: pass

        def ch(ok, path, err): self._send("download_done", did, ok, path, err)
        self._send("dl_progress", did, -1, "Connecting...")
        dl.run(progress_hook=ph, completion_hook=ch, ffmpeg_progress_hook=ffp)

    def _on_cancel(self):
        for did, d in self._downloads.items():
            if d.get("active") and "downloader" in d:
                d["downloader"].cancel()
                if "status_lbl" in d: d["status_lbl"].config(text="Cancelling…", fg=self.C["text2"])
                if "cancel_btn" in d: d["cancel_btn"].config(state="disabled")
        self._status_var.set("Cancelling…"); self._upd_cancel()

    def _on_clear(self):
        to_remove = [did for did, d in self._downloads.items() if not d.get("active")]
        for did in to_remove:
            dl = self._downloads[did]
            if "row_frame" in dl: dl["row_frame"].destroy()
            if "pbar" in dl and dl["pbar"] in self._pbars: self._pbars.remove(dl["pbar"])
            del self._downloads[did]
        self._update_dl_count(); self._upd_clear()
        if not self._downloads: self._dl_ph.pack(pady=36)

    def _on_browse(self):
        f = filedialog.askdirectory(initialdir=self._output_dir_var.get() or os.getcwd())
        if f: self._output_dir_var.set(f)

    def _on_fmt_change(self):
        fmt = self._format_var.get()
        if fmt == "mp3":
            self._res_combo.config(state="disabled")
            self._mp3_combo.config(state="readonly" if self.video_info else "disabled")
        else:
            self._res_combo.config(state="readonly" if self.video_info else "disabled")
            self._mp3_combo.config(state="disabled")

    def _open_settings(self):
        win = tk.Toplevel(self.root); win.title("Settings"); win.geometry("400x350")
        win.transient(self.root); win.grab_set(); win.configure(bg=self.C["bg"])
        
        tk.Label(win, text="Settings", font=(FONT, 16, "bold"), bg=self.C["bg"], fg=self.C["text"]).pack(pady=20)
        
        sound_var = tk.BooleanVar(value=self._settings["sound_on_finish"])
        notif_var = tk.BooleanVar(value=self._settings["notifications"])
        bg_var = tk.BooleanVar(value=self._settings["background_download"])
        
        def make_toggle(var, text, key):
            frame = tk.Frame(win, bg=self.C["bg"]); frame.pack(pady=10, fill=tk.X, padx=40)
            tk.Checkbutton(frame, text=text, variable=var, bg=self.C["bg"], fg=self.C["text"],
                           font=(FONT, 11), selectcolor=self.C["entry_bg"], activebackground=self.C["bg"],
                           activeforeground=self.C["text"],
                           command=lambda: self._settings.update({key: var.get()})).pack(side=tk.LEFT)
                           
        make_toggle(sound_var, "Play sound on finish", "sound_on_finish")
        make_toggle(notif_var, "Show Windows notification", "notifications")
        make_toggle(bg_var, "Run in background when closed", "background_download")
        
        def close():
            self._save_settings(); win.destroy()
        tk.Button(win, text="Save", command=close, font=(FONT, 11, "bold"), bg=self.C["primary"], fg="white", relief="flat", padx=20, pady=8).pack(pady=30)

    def _on_help(self):
        messagebox.showinfo("Help", f"{APP_TITLE} v{APP_VERSION}\n\n1. Paste a YouTube URL\n2. Click Fetch\n3. Choose format (MP4/MP3) and quality\n4. Click Download\n\nMultiple simultaneous downloads supported!\nClick 'Clear' to remove finished downloads.")

    def _toggle_dark(self):
        self._dark = not self._dark; self.C = DARK if self._dark else LIGHT; self._apply_theme()

    def _open_folder(self, path):
        folder = os.path.dirname(path) if path else self._output_dir_var.get()
        try:
            if os.name == "nt": os.startfile(folder)
            elif sys.platform == "darwin": os.system(f'open "{folder}"')
            else: os.system(f'xdg-open "{folder}"')
        except: pass

    def _mk_row(self, did, title):
        self._dl_ph.pack_forget(); C = self.C; fmt = self._format_var.get()
        outer = tk.Frame(self._dl_inner, bg=C["card"], padx=1, pady=1, highlightbackground=C["card_border"], highlightthickness=1); outer.pack(fill=tk.X, pady=6, padx=4)
        inner = tk.Frame(outer, bg=C["card"], padx=16, pady=12); inner.pack(fill=tk.X, expand=True)
        arrow = tk.Label(inner, text="▼", font=(FONT, 10), bg=C["card"], fg=C["text2"])
        arrow.pack(side=tk.LEFT, anchor="n")
        main = tk.Frame(inner, bg=C["card"])
        main.pack(side=tk.LEFT, fill=tk.X, expand=True)
        top = tk.Frame(main, bg=C["card"]); top.pack(fill=tk.X)
        thumb = tk.Label(top, text=f"\n{IC['video']}", font=(FONT, 14), bg=C["entry_bg"], fg=C["text3"], width=18, height=5, highlightbackground=C["card_border"], highlightthickness=1); thumb.pack(side=tk.LEFT, padx=(0, 16))
        info_col = tk.Frame(top, bg=C["card"]); info_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        t_row = tk.Frame(info_col, bg=C["card"]); t_row.pack(fill=tk.X)
        title_lbl = tk.Label(t_row, text=title[:60] + ("..." if len(title) > 60 else ""), font=(FONT, 11, "bold"), bg=C["card"], fg=C["text"], anchor="w"); title_lbl.pack(side=tk.LEFT)
        fmt_badge = tk.Label(t_row, text=fmt.upper(), font=(FONT, 8, "bold"), bg=C["primary"], fg=C["primary_fg"], padx=8, pady=2); fmt_badge.pack(side=tk.LEFT, padx=(10, 0))
        meta_lbl = tk.Label(info_col, text="0% Complete     0.0MB / 0.0MB     0.0MB/s", font=(FONT, 10), bg=C["card"], fg=C["text2"], anchor="w"); meta_lbl.pack(fill=tk.X, pady=(4, 0))
        pbar = _PBar(main, h=14, C=C); pbar.pack(fill=tk.X, pady=(12, 6)); pbar.start_ind(); self._pbars.append(pbar)
        bot = tk.Frame(main, bg=C["card"]); bot.pack(fill=tk.X)
        status_lbl = tk.Label(bot, text="Starting...", font=(FONT, 10), bg=C["card"], fg=C["text2"], anchor="w"); status_lbl.pack(side=tk.LEFT)
        btn_f = tk.Frame(bot, bg=C["card"]); btn_f.pack(side=tk.RIGHT)
        cancel_btn = self._btn(btn_f, "", lambda: self._cancel_one(did), "ghost", IC["cancel"]); cancel_btn.config(state="normal"); cancel_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._downloads.setdefault(did, {})
        self._downloads[did].update(row_frame=outer, inner_frame=main, pbar=pbar, title_lbl=title_lbl, meta_lbl=meta_lbl, status_lbl=status_lbl, thumb=thumb, cancel_btn=cancel_btn, fmt_badge=fmt_badge, arrow=arrow, expanded=True, has_total=False, last_pct=0, stream_num=1)
        def toggle():
            dl = self._downloads[did]
            if dl["expanded"]:
                dl["inner_frame"].pack_forget(); dl["arrow"].config(text="▶"); dl["expanded"] = False
            else:
                dl["inner_frame"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True); dl["arrow"].config(text="▼"); dl["expanded"] = True
        arrow.bind("<Button-1>", lambda e: toggle())
        title_lbl.bind("<Button-1>", lambda e: toggle())

    def _upd_row(self, did, pct=0, text=""):
        dl = self._downloads.get(did)
        if not dl or "pbar" not in dl: return
        pb = dl["pbar"]
        if text:
            if "status_lbl" in dl: dl["status_lbl"].config(text=text)
            if "meta_lbl" in dl: dl["meta_lbl"].config(text=text)
        if pct >= 0:
            if not dl.get("has_total"): dl["has_total"] = True; pb.stop()
            pb.set(max(pct, 0))

    def _update_dl_count(self):
        active = sum(1 for d in self._downloads.values() if d.get("active"))
        total = len(self._downloads)
        if hasattr(self, "_dl_count"): self._dl_count.config(text=f"{active} active / {total} total" if total else "")

    def _fin_row(self, did, ok, path, err):
        dl = self._downloads.get(did); C = self.C
        if dl:
            dl["active"] = False
            if "pbar" in dl: dl["pbar"].stop(); dl["pbar"].set_done(ok)
            if "status_lbl" in dl:
                if ok and path: t = f'{IC["check"]} Complete!  {os.path.basename(path)}'
                elif ok: t = f'{IC["check"]} Complete!'
                elif err and "cancelled" in err.lower(): t = f'{IC["cross"]} Cancelled'
                elif err: t = f'{IC["cross"]} Failed: {err}'
                else: t = f'{IC["cross"]} Cancelled'
                dl["status_lbl"].config(text=t, fg=C["ok"] if ok else C["err"])
            if "meta_lbl" in dl: dl["meta_lbl"].config(text="")
            if "title_lbl" in dl: dl["title_lbl"].config(fg=C["ok"] if ok else C["text3"])
            if "cancel_btn" in dl:
                if ok and path: dl["cancel_btn"].config(text=f" {IC['open']} ", state="normal", fg=C["btn_fg"], command=lambda p=path: self._open_folder(p))
                else: dl["cancel_btn"].config(state="disabled")
        self._idle(); self._upd_cancel(); self._upd_clear(); self._update_dl_count()
        
        # Background execution logic
        if not any(d.get("active") for d in self._downloads.values()):
            if self._is_background:
                if ok:
                    if self._settings["sound_on_finish"]: self._play_sound()
                    if self._settings["notifications"]: self._show_notification("Download Complete", f"Saved to: {path}")
                self.root.destroy()
            else:
                if ok: messagebox.showinfo("Done", f"Download complete!\n\nSaved to:\n{path}" if path else "Download complete!")
                elif err and "cancelled" not in err.lower(): messagebox.showwarning("Download", err)
                if not self._downloads: self._dl_ph.pack(pady=36)

    def _cancel_one(self, did):
        dl = self._downloads.get(did)
        if dl and dl.get("active") and "downloader" in dl:
            dl["downloader"].cancel()
            if "status_lbl" in dl: dl["status_lbl"].config(text="Cancelling…", fg=self.C["text2"])
            if "cancel_btn" in dl: dl["cancel_btn"].config(state="disabled")

    def _play_sound(self):
        try:
            import winsound
            winsound.Beep(523, 200); winsound.Beep(659, 200); winsound.Beep(783, 300)
        except: pass

    def _show_notification(self, title, message):
        try:
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("YT Downloader").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        except: pass

    def on_close(self):
        active = sum(1 for d in self._downloads.values() if d.get("active"))
        if active and self._settings["background_download"]:
            if messagebox.askyesno("Background Download", f"There {'is' if active == 1 else 'are'} {active} active download(s).\n\nKeep running in the background?"):
                self.root.withdraw()
                self._is_background = True
                return
        for d in self._downloads.values():
            if d.get("active") and "downloader" in d: d["downloader"].cancel()
        self.root.destroy()

def main():
    def _bring_to_front(root):
        try:
            root.deiconify(); root.lift(); root.attributes("-topmost", True)
            root.after(100, lambda: root.attributes("-topmost", False))
            try: root.focus_force()
            except: pass
        except: pass

    def ipc_server(app):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', IPC_PORT))
            s.listen(5)
        except Exception:
            try: s.close()
            except: pass
            return
        while True:
            try:
                conn, _ = s.accept()
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk: break
                    data += chunk
                conn.close()
                try:
                    txt = data.decode('utf-8', errors='ignore').strip()
                    if txt:
                        try:
                            msg = json.loads(txt)
                        except Exception:
                            msg = {"url": txt, "fetch": False}
                        def _set():
                            try:
                                url = msg.get('url') if isinstance(msg, dict) else txt
                                fetch = bool(msg.get('fetch')) if isinstance(msg, dict) else False
                                app._url_var.set(url)
                                app._url_ph = False
                                try:
                                    w = app.url_entry.entry if hasattr(app.url_entry, 'entry') else app.url_entry
                                    w.delete(0, tk.END); w.insert(0, url)
                                except: pass
                                _bring_to_front(app.root)
                                if fetch:
                                    app._on_fetch()
                            except: pass
                        app.root.after(0, _set)
                except: pass
            except Exception:
                try: conn.close()
                except: pass
                continue

    def send_ipc_message(url, fetch=False):
        try:
            msg = json.dumps({"url": url, "fetch": bool(fetch)})
            with socket.create_connection(('127.0.0.1', IPC_PORT), timeout=1) as s:
                s.sendall(msg.encode('utf-8'))
            return True
        except Exception:
            return False

    # Parse command-line URL if present
    url_arg = None
    url_fetch = False
    if len(sys.argv) > 1:
        a = sys.argv[1]
        if a.startswith("http://") or a.startswith("https://"):
            url_arg = a

    # If an instance is already running, forward the URL and exit
    if url_arg:
        if send_ipc_message(url_arg, url_fetch):
            sys.exit(0)

    root = tk.Tk()
    app = YTDownloaderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    # Start IPC server to accept forwarded URLs from new instances
    t = threading.Thread(target=ipc_server, args=(app,), daemon=True)
    t.start()

    # If we were launched with a URL and no running instance existed, set it now
    if url_arg:
        def _apply():
            try:
                app._url_var.set(url_arg); app._url_ph = False
                try:
                    w = app.url_entry.entry if hasattr(app.url_entry, 'entry') else app.url_entry
                    w.delete(0, tk.END); w.insert(0, url_arg)
                except: pass
                _bring_to_front(app.root)
                if url_fetch:
                    app._on_fetch()
            except: pass
        app.root.after(200, _apply)

    root.mainloop()

if __name__ == "__main__":
    main()