# -*- coding: utf-8 -*-
"""
دانلودگر ویدئو - نسخه Kivy (تم تیره / سبز نئونی)
"""
import os
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.graphics import Color, RoundedRectangle

import yt_dlp

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
INPUTBG  = (0.93,  0.95,  0.94,  1)   # زمینه روشن کادر ورودی (برای خوانایی قطعی)
INPUTTX  = (0.06,  0.08,  0.07,  1)   # متن تیره روی زمینه روشن

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

        if ANDROID:
            try:
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                ])
            except Exception:
                pass

        root = BoxLayout(orientation="vertical",
                         padding=[dp(22), dp(30), dp(22), dp(22)],
                         spacing=dp(12))

        root.add_widget(Label(text=fa("دانلود ویدئو"),
                              size_hint_y=None, height=dp(46),
                              font_size="26sp", bold=True, color=TEXT))

        bar_wrap = BoxLayout(size_hint_y=None, height=dp(4))
        bar = Widget(size_hint_x=None, width=dp(64))
        round_bg(bar, ACCENT, radius=2)
        bar_wrap.add_widget(Widget())
        bar_wrap.add_widget(bar)
        bar_wrap.add_widget(Widget())
        root.add_widget(bar_wrap)

        root.add_widget(Widget(size_hint_y=None, height=dp(10)))

        # ---- لینک ویدئو + دکمه پاک‌کردن ----
        root.add_widget(self._label(fa("لینک ویدئو")))
        url_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.url = self._input(hint=fa("لینک را اینجا بچسبانید"))
        clear_btn = Button(text="✕", size_hint_x=None, width=dp(52),
                           background_normal="", background_down="",
                           background_color=(0, 0, 0, 0),
                           color=TEXT, font_size="20sp")
        round_bg(clear_btn, SURFACE, 14)
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

        # ---- محل ذخیره + دکمه انتخاب پوشه ----
        root.add_widget(self._label(fa("محل ذخیره")))
        path_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.path = self._input(text=default_dir(), font_size="13sp")
        browse_btn = Button(text=fa("انتخاب"), size_hint_x=None, width=dp(90),
                            background_normal="", background_down="",
                            background_color=(0, 0, 0, 0),
                            color=ACCENT, bold=True, font_size="14sp")
        round_bg(browse_btn, SURFACE, 14)
        browse_btn.bind(on_release=self.open_folder_chooser)
        path_row.add_widget(self.path)
        path_row.add_widget(browse_btn)
        root.add_widget(path_row)

        root.add_widget(Widget(size_hint_y=None, height=dp(6)))

        # ---- دکمه دانلود ----
        self.btn = Button(text=fa("دانلود"),
                          size_hint_y=None, height=dp(56),
                          background_normal="", background_down="",
                          background_color=(0, 0, 0, 0),
                          color=DARKTX, bold=True, font_size="18sp")
        round_bg(self.btn, ACCENT, 16)
        self.btn.bind(on_release=self.on_download)
        self.btn.bind(state=self._btn_state)
        root.add_widget(self.btn)

        self.progress = NeonProgress(size_hint_y=None, height=dp(8))
        root.add_widget(self.progress)

        self.status = Label(text="", size_hint_y=None, height=dp(80),
                            font_size="14sp", color=MUTED,
                            halign="center", valign="top")
        self.status.bind(size=lambda *_: setattr(self.status, "text_size",
                                                 (self.status.width, None)))
        root.add_widget(self.status)

        root.add_widget(Widget())
        return root

    # ---------- سازنده‌های ویجت ----------
    def _label(self, text):
        lbl = Label(text=text, size_hint_y=None, height=dp(22),
                    color=MUTED, font_size="13sp",
                    halign="right", valign="middle")
        lbl.bind(size=lambda *_: setattr(lbl, "text_size", (lbl.width, lbl.height)))
        return lbl

    def _input(self, text="", hint="", font_size="16sp"):
        # زمینه روشن + متن تیره تا خوانایی قطعی باشد
        ti = TextInput(text=text, hint_text=hint, multiline=False,
                       size_hint_y=None, height=dp(52),
                       background_color=INPUTBG, foreground_color=INPUTTX,
                       cursor_color=ACCENT_D, hint_text_color=MUTED,
                       font_size=font_size,
                       padding=[dp(16), dp(15), dp(16), dp(15)])
        return ti

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
        # filters بالا فایل‌ها را پنهان می‌کند و فقط پوشه‌ها نمایش داده می‌شوند

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

    # ---------- منطق دانلود ----------
    def on_download(self, *_):
        url = self.url.text.strip()
        if not url:
            self.set_status(fa("لینک را وارد کنید"), RED)
            return
        fmt = QUALITY.get(self.quality.text, "best")
        path = self.path.text.strip() or default_dir()
        self.btn.disabled = True
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
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            self._done(fa("کامل شد: ") + str(info.get("title", "")), ACCENT)
        except Exception as e:
            self._done(fa("خطا: ") + str(e), RED)

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            self._progress(pct, fa("در حال دانلود ") + "%d%%" % pct)
        elif d["status"] == "finished":
            self._progress(100, fa("در حال نهایی‌سازی..."))

    @mainthread
    def _progress(self, pct, text):
        self.progress.value = pct
        self.status.text = text
        self.status.color = TEXT

    @mainthread
    def _done(self, text, color):
        self.status.text = text
        self.status.color = color
        self.btn.disabled = False

    @mainthread
    def set_status(self, text, color=MUTED):
        self.status.text = text
        self.status.color = color


if __name__ == "__main__":
    Downloader().run()
