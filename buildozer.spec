[app]

# نام و شناسه برنامه
title = Video Downloader
package.name = ytdownloader
package.domain = org.mydownloader

# منبع کد
source.dir = .
source.include_exts = py,ttf

version = 1.0

# کتابخانه‌های موردنیاز
# python-bidi روی نسخه ۰.۴.۲ پین شده تا نیازی به کامپایلر Rust نداشته باشد
requirements = python3,kivy,yt-dlp,arabic-reshaper,python-bidi==0.4.2,certifi

orientation = portrait
fullscreen = 0

# ---------- تنظیمات اندروید ----------
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.allow_backup = 1


[buildozer]
log_level = 2
warn_on_root = 1
