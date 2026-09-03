# -*- coding: utf-8 -*-
"""
دانلودگر ویدئو - نسخه Kivy برای ساخت APK
"""
import os
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.metrics import dp

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

# ---------- ثبت فونت فارسی (در صورت وجود) ----------
FONT = None
for _p in ("Vazirmatn-Regular.ttf", "Vazir.ttf"):
    if os.path.exists(_p):
        LabelBase.register(name="fa", fn_regular=_p)
        FONT = "fa"
        break

# ---------- امکانات اندروید ----------
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    ANDROID = True
except Exception:
    ANDROID = False

# ---------- کیفیت‌ها (فرمت‌های تک‌فایل، بدون نیاز به ffmpeg) ----------
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


class Downloader(App):
    def build(self):
        self.title = "Video Downloader"
        if ANDROID:
            try:
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                ])
            except Exception:
                pass

        fk = {"font_name": FONT} if FONT else {}
        self._fk = fk

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))

        root.add_widget(Label(text=fa("⬇️ دانلود ویدئو"),
                              size_hint_y=None, height=dp(44),
                              font_size="22sp", **fk))

        root.add_widget(self._lbl(fa("لینک ویدئو:")))
        self.url = TextInput(multiline=False, size_hint_y=None, height=dp(46),
                             font_size="15sp")
        root.add_widget(self.url)

        root.add_widget(self._lbl(fa("کیفیت:")))
        self.quality = Spinner(text=list(QUALITY.keys())[0],
                               values=list(QUALITY.keys()),
                               size_hint_y=None, height=dp(46), **fk)
        root.add_widget(self.quality)

        root.add_widget(self._lbl(fa("محل ذخیره:")))
        self.path = TextInput(text=default_dir(), multiline=False,
                              size_hint_y=None, height=dp(46), font_size="13sp")
        root.add_widget(self.path)

        self.btn = Button(text=fa("دانلود"), size_hint_y=None, height=dp(52),
                          font_size="17sp", **fk)
        self.btn.bind(on_release=self.on_download)
        root.add_widget(self.btn)

        self.progress = ProgressBar(max=100, value=0,
                                    size_hint_y=None, height=dp(18))
        root.add_widget(self.progress)

        self.status = Label(text="", size_hint_y=None, height=dp(70),
                            font_size="14sp", halign="center", valign="top", **fk)
        self.status.bind(size=lambda *_: setattr(self.status, "text_size",
                                                 self.status.size))
        root.add_widget(self.status)

        root.add_widget(Label())  # فضای خالی پایین
        return root

    def _lbl(self, text):
        return Label(text=text, size_hint_y=None, height=dp(24),
                     halign="right", font_size="13sp", **self._fk)

    def on_download(self, *_):
        url = self.url.text.strip()
        if not url:
            self.set_status(fa("لینک را وارد کنید"))
            return
        fmt = QUALITY.get(self.quality.text, "best")
        path = self.path.text.strip() or default_dir()
        self.btn.disabled = True
        self.progress.value = 0
        self.set_status(fa("در حال شروع..."))
        threading.Thread(target=self._run, args=(url, fmt, path),
                         daemon=True).start()

    def _run(self, url, fmt, path):
        try:
            os.makedirs(path, exist_ok=True)
            opts = {
                "format": fmt,
                "outtmpl": os.path.join(path, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "progress_hooks": [self._hook],
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            self._done(fa("✅ کامل شد: ") + str(info.get("title", "")))
        except Exception as e:
            self._done(fa("خطا: ") + str(e))

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

    @mainthread
    def _done(self, text):
        self.status.text = text
        self.btn.disabled = False

    @mainthread
    def set_status(self, text):
        self.status.text = text


if __name__ == "__main__":
    Downloader().run()
