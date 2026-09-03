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
# python-bidi روی ۰.۴.۲ پین شده تا نیازی به Rust نداشته باشد
# charset-normalizer روی ۲.۱.۱ پین شده چون این نسخه خالص پایتون است و بخش C ندارد
requirements = python3,kivy,yt-dlp,arabic-reshaper,python-bidi==0.4.2,charset-normalizer==2.1.1,certifi

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
