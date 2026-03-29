[app]

title = 智能计薪系统
package.name = salaryapp
package.domain = org.salaryapp

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db

version = 1.0.0

requirements = python3,kivy

orientation = portrait

fullscreen = 0

android.permissions = INTERNET

[buildozer]

log_level = 2

warn_on_root = 0

android.api = 34

android.minapi = 21

android.ndk = 25b

android.ndk_api = 21

android.accept_sdk_license = True
