[app]
title = Mis Finanzas
package.name = misfinanzas
package.domain = org.miguelp26b
source.dir = .
source.include_exts = py
source.exclude_dirs = tests, bin, .github, .buildozer, venv
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk

# Versión estable de python-for-android (la rama de desarrollo falla con Python 3.14).
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
