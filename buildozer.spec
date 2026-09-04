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
# python-bidi و charset-normalizer روی نسخه‌های خالص پایتون پین شده‌اند
requirements = python3,kivy,yt-dlp,arabic-reshaper,python-bidi==0.4.2,charset-normalizer==2.1.1,certifi

# مهم: استفاده از نسخه پایدار python-for-android (هدف = پایتون ۳.۱۱)
# بدون این، نسخه توسعه استفاده می‌شود که پایتون ۳.۱۴ را هدف می‌گیرد و بیلد می‌شکند
p4a.fork = kivy
p4a.branch = v2024.01.21

orientation = portrait
fullscreen = 0

# ---------- تنظیمات اندروید ----------
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.allow_backup = 1


[buildozer]
log_level = 2
warn_on_root = 1
