[app]

# (str) Title of your application
title = SSH VPN

# (str) Package name
package.name = sshvpn

# (str) Package domain (needed for android/ios packaging)
package.domain = org.sshvpn

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# (list) Source files to exclude
source.exclude_dirs = tests, bin, node_modules, .next, app, components, hooks, lib, public, styles

# (str) Application versioning
version = 1.0

# (list) Application requirements
# Comma separated python modules / recipes to bundle into the APK.
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,paramiko,cryptography,bcrypt,pynacl,six,arabic_reshaper,python-bidi

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

#
# Android specific
#
android.accept_sdk_license = True
android.skip_update = False

# (list) Permissions
# INTERNET is required for SSH; the others help with networking state.
android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 23

# (str) Android NDK version to use
#android.ndk = 25b

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk).
android.release_artifact = apk

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
