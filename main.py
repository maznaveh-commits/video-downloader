# -*- coding: utf-8 -*-
"""
دانلودگر ویدئو - نسخه Kivy (تم تیره / سبز نئونی)
"""
import os
import json
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.graphics import Color, RoundedRectangle

import yt_dlp

# ---------- شماره نسخه برنامه ----------
VERSION = "1.0"

# ---------- شکل‌دهی صحیح متن فارسی ----------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def fa(t):
        return get_display(arabic_reshaper.reshape(str(t)))
except Exception:
    def fa(t):
        return str(t)

# ---------- ثبت فونت فارسی به‌عنوان فونت پیش‌فرض ----------
for _p in ("Vazirmatn-Regular.ttf", "Vazir.ttf"):
    if os.path.exists(_p):
        LabelBase.register(name="Roboto", fn_regular=_p)
        LabelBase.register(name="fa", fn_regular=_p)
        break

# ---------- امکانات اندروید ----------
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    ANDROID = True
except Exception:
    ANDROID = False


def ensure_all_files_access():
    """در اندروید ۱۱+ اجازه نوشتن در همه‌ی پوشه‌ها را می‌گیرد."""
    if not ANDROID:
        return
    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        VERSION = autoclass("android.os.Build$VERSION")
        if VERSION.SDK_INT >= 30 and not Environment.isExternalStorageManager():
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            intent = Intent(
                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
            intent.setData(Uri.parse("package:" + activity.getPackageName()))
            activity.startActivity(intent)
    except Exception:
        pass


def open_file(path):
    """باز کردن فایل با پخش‌کننده‌ی پیش‌فرض گوشی."""
    if not (ANDROID and path and os.path.exists(path)):
        return False
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        File = autoclass("java.io.File")
        StrictMode = autoclass("android.os.StrictMode")
        StrictMode.disableDeathOnFileUriExposure()
        activity = PythonActivity.mActivity
        low = path.lower()
        if low.endswith((".mp4", ".mkv", ".webm", ".mov")):
            mime = "video/*"
        elif low.endswith((".m4a", ".mp3", ".aac", ".opus", ".ogg", ".wav")):
            mime = "audio/*"
        else:
            mime = "*/*"
        intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(Uri.fromFile(File(path)), mime)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
        return True
    except Exception:
        return False


class _Cancelled(Exception):
    pass


# ---------- پالت رنگ (تیره / سبز نئونی) ----------
BG       = (0.043, 0.055, 0.051, 1)
SURFACE  = (0.094, 0.114, 0.106, 1)
ACCENT   = (0.0,   0.902, 0.463, 1)
ACCENT_D = (0.0,   0.62,  0.33,  1)
TEXT     = (0.906, 0.941, 0.925, 1)
MUTED    = (0.48,  0.545, 0.51,  1)
DARKTX   = (0.04,  0.06,  0.05,  1)
RED      = (1.0,   0.42,  0.42,  1)
TRACK    = (0.16,  0.19,  0.17,  1)
INPUTBG  = (0.93,  0.95,  0.94,  1)
INPUTTX  = (0.06,  0.08,  0.07,  1)

# ---------- کیفیت‌ها ----------
QUALITY = {
    fa("بهترین (تک‌فایل)"): "best[ext=mp4]/best",
    fa("۷۲۰p"): "best[height<=720][ext=mp4]/best[height<=720]",
    fa("۴۸۰p"): "best[height<=480][ext=mp4]/best[height<=480]",
    fa("۳۶۰p"): "best[height<=360][ext=mp4]/best[height<=360]",
    fa("فقط صدا (m4a)"): "bestaudio[ext=m4a]/bestaudio",
}


def default_dir():
    if ANDROID:
        try:
            return os.path.join(primary_external_storage_path(), "Download")
        except Exception:
            pass
    return os.path.expanduser("~")


def cookie_file_for(url):
    """اگر فایل کوکی مناسب در پوشه Download باشد، مسیرش را برمی‌گرداند."""
    d = default_dir()
    u = (url or "").lower()
    if "instagram.com" in u:
        names = ["instagram_cookies.txt", "cookies_instagram.txt"]
    elif "youtu" in u:
        names = ["youtube_cookies.txt", "cookies_youtube.txt"]
    else:
        names = []
    names.append("cookies.txt")  # فایل عمومی به‌عنوان پشتیبان
    for n in names:
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    return None


def round_bg(widget, rgba, radius=14):
    with widget.canvas.before:
        widget._bgc = Color(*rgba)
        widget._bgr = RoundedRectangle(radius=[radius], pos=widget.pos, size=widget.size)

    def _upd(*_a):
        widget._bgr.pos = widget.pos
        widget._bgr.size = widget.size
    widget.bind(pos=_upd, size=_upd)


class NeonProgress(Widget):
    value = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            Color(*TRACK)
            self._track = RoundedRectangle(radius=[6])
            Color(*ACCENT)
            self._fill = RoundedRectangle(radius=[6])
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw)

    def _redraw(self, *_a):
        self._track.pos = self.pos
        self._track.size = self.size
        self._fill.pos = self.pos
        w = self.width * max(0, min(self.value, 100)) / 100.0
        self._fill.size = (w, self.height)


class Downloader(App):

    def build(self):
        self.title = "Video Downloader"
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        self._downloading = False
        self._cancel = False
        self._last_file = None

        if ANDROID:
            try:
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                ])
            except Exception:
                pass
            ensure_all_files_access()

        root = BoxLayout(orientation="vertical",
                         padding=[dp(20), dp(26), dp(20), dp(18)],
                         spacing=dp(10))

        root.add_widget(Label(text=fa("دانلود ویدئو"),
                              size_hint_y=None, height=dp(42),
                              font_size="25sp", bold=True, color=TEXT))

        bar_wrap = BoxLayout(size_hint_y=None, height=dp(4))
        bar = Widget(size_hint_x=None, width=dp(64))
        round_bg(bar, ACCENT, radius=2)
        bar_wrap.add_widget(Widget())
        bar_wrap.add_widget(bar)
        bar_wrap.add_widget(Widget())
        root.add_widget(bar_wrap)

        root.add_widget(Label(text="v" + VERSION, size_hint_y=None,
                              height=dp(18), font_size="11sp", color=MUTED))

        root.add_widget(Widget(size_hint_y=None, height=dp(8)))

        # ---- لینک ویدئو + دکمه پاک ----
        root.add_widget(self._label(fa("لینک ویدئو")))
        url_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.url = self._input(hint=fa("لینک را اینجا بچسبانید"))
        clear_btn = self._chip(fa("پاک"), ACCENT, width=dp(64))
        clear_btn.bind(on_release=lambda *_: setattr(self.url, "text", ""))
        url_row.add_widget(self.url)
        url_row.add_widget(clear_btn)
        root.add_widget(url_row)

        # ---- کیفیت ----
        root.add_widget(self._label(fa("کیفیت")))
        self.quality = Spinner(
            text=list(QUALITY.keys())[0],
            values=list(QUALITY.keys()),
            size_hint_y=None, height=dp(52),
            background_normal="", background_color=(0, 0, 0, 0),
            color=TEXT, font_size="16sp")
        round_bg(self.quality, SURFACE, 14)
        root.add_widget(self.quality)

        # ---- محل ذخیره + انتخاب ----
        root.add_widget(self._label(fa("محل ذخیره")))
        path_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.path = self._input(text=default_dir(), font_size="13sp")
        browse_btn = self._chip(fa("انتخاب"), ACCENT, width=dp(88))
        browse_btn.bind(on_release=self.open_folder_chooser)
        path_row.add_widget(self.path)
        path_row.add_widget(browse_btn)
        root.add_widget(path_row)

        root.add_widget(Widget(size_hint_y=None, height=dp(6)))

        # ---- دکمه دانلود / لغو ----
        self.btn = Button(text=fa("دانلود"),
                          size_hint_y=None, height=dp(54),
                          background_normal="", background_down="",
                          background_color=(0, 0, 0, 0),
                          color=DARKTX, bold=True, font_size="18sp")
        round_bg(self.btn, ACCENT, 16)
        self.btn.bind(on_release=self.on_download)
        self.btn.bind(state=self._btn_state)
        root.add_widget(self.btn)

        self.progress = NeonProgress(size_hint_y=None, height=dp(8))
        root.add_widget(self.progress)

        self.status = Label(text="", size_hint_y=None, height=dp(84),
                            font_size="13sp", color=MUTED,
                            halign="center", valign="middle")
        self.status.bind(size=lambda *_: setattr(
            self.status, "text_size", (self.status.width, self.status.height)))
        root.add_widget(self.status)

        # ---- دکمه باز کردن فایل (بعد از تکمیل نمایان می‌شود) ----
        self.open_btn = Button(text=fa("باز کردن فایل"),
                               size_hint_y=None, height=dp(48),
                               background_normal="", background_down="",
                               background_color=(0, 0, 0, 0),
                               color=ACCENT, bold=True, font_size="15sp",
                               opacity=0, disabled=True)
        round_bg(self.open_btn, SURFACE, 14)
        self.open_btn.bind(on_release=lambda *_: self._open_last())
        root.add_widget(self.open_btn)

        # ---- سابقه دانلودها ----
        hist_btn = Button(text=fa("سابقه دانلودها"),
                          size_hint_y=None, height=dp(46),
                          background_normal="", background_down="",
                          background_color=(0, 0, 0, 0),
                          color=MUTED, font_size="14sp")
        round_bg(hist_btn, BG, 14)
        hist_btn.bind(on_release=self.open_history)
        root.add_widget(hist_btn)

        root.add_widget(Widget())
        return root

    # ---------- سازنده‌های ویجت ----------
    def _label(self, text):
        lbl = Label(text=text, size_hint_y=None, height=dp(20),
                    color=MUTED, font_size="13sp",
                    halign="right", valign="middle")
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, lbl.height)))
        return lbl

    def _input(self, text="", hint="", font_size="16sp"):
        return TextInput(text=text, hint_text=hint, multiline=False,
                         size_hint_y=None, height=dp(52),
                         background_color=INPUTBG, foreground_color=INPUTTX,
                         cursor_color=ACCENT_D, hint_text_color=MUTED,
                         font_size=font_size,
                         padding=[dp(16), dp(15), dp(16), dp(15)])

    def _chip(self, text, color, width=dp(80)):
        b = Button(text=text, size_hint_x=None, width=width,
                   background_normal="", background_down="",
                   background_color=(0, 0, 0, 0),
                   color=color, bold=True, font_size="14sp")
        round_bg(b, SURFACE, 14)
        return b

    def _btn_state(self, btn, state):
        btn._bgc.rgba = ACCENT_D if state == "down" else ACCENT

    # ---------- انتخاب گرافیکی پوشه ----------
    def open_folder_chooser(self, *_):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        start = self.path.text.strip() or default_dir()
        if not os.path.isdir(start):
            start = default_dir()

        chooser = FileChooserListView(path=start, dirselect=True,
                                      filters=[lambda folder, name: False])

        btns = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        pick = Button(text=fa("انتخاب این پوشه"), background_normal="",
                      background_color=(0, 0, 0, 0), color=DARKTX, bold=True)
        round_bg(pick, ACCENT, 12)
        cancel = Button(text=fa("انصراف"), background_normal="",
                        background_color=(0, 0, 0, 0), color=TEXT)
        round_bg(cancel, SURFACE, 12)
        btns.add_widget(pick)
        btns.add_widget(cancel)

        box.add_widget(chooser)
        box.add_widget(btns)

        popup = Popup(title=fa("انتخاب پوشه ذخیره"),
                      content=box, size_hint=(0.95, 0.9),
                      title_color=TEXT, separator_color=ACCENT)

        def _do_pick(*_a):
            sel = chooser.selection
            chosen = sel[0] if sel else chooser.path
            if chosen and os.path.isfile(chosen):
                chosen = os.path.dirname(chosen)
            self.path.text = chosen or start
            popup.dismiss()

        pick.bind(on_release=_do_pick)
        cancel.bind(on_release=lambda *_a: popup.dismiss())
        popup.open()

    # ---------- سابقه دانلودها ----------
    def _hist_path(self):
        return os.path.join(self.user_data_dir, "history.json")

    def _load_history(self):
        try:
            with open(self._hist_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _add_history(self, title, path):
        items = self._load_history()
        items.insert(0, {"title": title, "path": path})
        try:
            with open(self._hist_path(), "w", encoding="utf-8") as f:
                json.dump(items[:100], f, ensure_ascii=False)
        except Exception:
            pass

    def open_history(self, *_):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        items = self._load_history()

        if not items:
            box.add_widget(Label(text=fa("هنوز دانلودی ثبت نشده"), color=TEXT))
        else:
            scroll = ScrollView()
            inner = BoxLayout(orientation="vertical", size_hint_y=None,
                              spacing=dp(6), padding=[0, 0, 0, dp(4)])
            inner.bind(minimum_height=inner.setter("height"))
            for it in items:
                name = it.get("title") or os.path.basename(it.get("path", ""))
                exists = os.path.exists(it.get("path", ""))
                b = Button(text=fa(name), size_hint_y=None, height=dp(54),
                           background_normal="", background_down="",
                           background_color=(0, 0, 0, 0),
                           color=TEXT if exists else MUTED,
                           halign="right", valign="middle", font_size="13sp",
                           padding=[dp(12), dp(8)])
                b.bind(size=lambda w, *_: setattr(w, "text_size",
                                                  (w.width - dp(24), w.height)))
                round_bg(b, SURFACE, 10)
                b.bind(on_release=lambda _w, p=it.get("path"): open_file(p))
                inner.add_widget(b)
            scroll.add_widget(inner)
            box.add_widget(scroll)

        close = Button(text=fa("بستن"), size_hint_y=None, height=dp(48),
                       background_normal="", background_color=(0, 0, 0, 0),
                       color=DARKTX, bold=True)
        round_bg(close, ACCENT, 12)
        box.add_widget(close)

        popup = Popup(title=fa("سابقه دانلودها"), content=box,
                      size_hint=(0.95, 0.9),
                      title_color=TEXT, separator_color=ACCENT)
        close.bind(on_release=lambda *_a: popup.dismiss())
        popup.open()

    def _open_last(self):
        if not open_file(self._last_file):
            self.set_status(fa("باز کردن فایل ممکن نشد"), RED)

    # ---------- منطق دانلود ----------
    def on_download(self, *_):
        if self._downloading:
            self._cancel = True
            self.set_status(fa("در حال لغو..."), MUTED)
            return
        url = self.url.text.strip()
        if not url:
            self.set_status(fa("لینک را وارد کنید"), RED)
            return
        fmt = QUALITY.get(self.quality.text, "best")
        path = self.path.text.strip() or default_dir()
        self._downloading = True
        self._cancel = False
        self._last_file = None
        self.btn.text = fa("لغو دانلود")
        self._set_open(False)
        self.progress.value = 0
        self.set_status(fa("در حال شروع..."), MUTED)
        threading.Thread(target=self._run, args=(url, fmt, path),
                         daemon=True).start()

    def _run(self, url, fmt, path):
        class _Logger:
            def debug(self, m): pass
            def info(self, m): pass
            def warning(self, m): pass
            def error(self, m): pass

        try:
            os.makedirs(path, exist_ok=True)
            opts = {
                "format": fmt,
                "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "progress_hooks": [self._hook],
                "logger": _Logger(),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
            }
            cf = cookie_file_for(url)
            if cf:
                opts["cookiefile"] = cf
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = str(info.get("title", ""))
            self._add_history(title, self._last_file)
            self._finish(fa("کامل شد: ") + title, ACCENT, self._last_file)
        except _Cancelled:
            self._finish(fa("دانلود لغو شد"), MUTED, None)
        except Exception as e:
            self._finish(self._friendly_error(e), RED, None)

    def _friendly_error(self, e):
        s = str(e)
        low = s.lower()
        if ("sign in to confirm" in low or "cookies" in low
                or "login required" in low or "rate-limit" in low
                or "private" in low and "cookie" in low):
            return fa("نیاز به ورود. فایل کوکی را در پوشه Download بگذار.")
        if len(s) > 160:
            s = s[:160] + "…"
        return fa("خطا: ") + s

    def _hook(self, d):
        if self._cancel:
            raise _Cancelled()
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            self._progress(pct, fa("در حال دانلود ") + "%d%%" % pct)
        elif d["status"] == "finished":
            self._last_file = d.get("filename")
            self._progress(100, fa("در حال نهایی‌سازی..."))

    # ---------- به‌روزرسانی رابط (روی ریسه اصلی) ----------
    @mainthread
    def _progress(self, pct, text):
        self.progress.value = pct
        self.status.text = text
        self.status.color = TEXT

    @mainthread
    def _finish(self, text, color, file_path):
        self.status.text = text
        self.status.color = color
        self._downloading = False
        self.btn.text = fa("دانلود")
        if file_path and os.path.exists(file_path):
            self._last_file = file_path
            self._set_open(True)

    @mainthread
    def _set_open(self, show):
        self.open_btn.opacity = 1 if show else 0
        self.open_btn.disabled = not show

    @mainthread
    def set_status(self, text, color=MUTED):
        self.status.text = text
        self.status.color = color


if __name__ == "__main__":
    Downloader().run()
