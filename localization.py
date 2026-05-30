# -*- coding: utf-8 -*-
"""
Simple bilingual (English / Arabic) string table for the SSH VPN app.

Usage:
    from localization import tr, set_language, get_language, is_rtl

    set_language("ar")
    label = tr("connect")
"""

TRANSLATIONS = {
    "en": {
        "app_title": "SSH VPN",
        "app_subtitle": "Secure SSH tunnel client",
        "server_section": "Server",
        "host": "Host / IP address",
        "port": "Port",
        "username": "Username",
        "password": "Password",
        "local_port": "Local SOCKS port",
        "save": "Save",
        "saved": "Settings saved",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "status": "Status",
        "status_disconnected": "Disconnected",
        "status_connecting": "Connecting…",
        "status_connected": "Connected",
        "status_error": "Connection error",
        "proxy_hint": "SOCKS5 proxy running on 127.0.0.1:{port}",
        "language": "Language",
        "english": "English",
        "arabic": "العربية",
        "fill_fields": "Please fill in host, username and password",
        "bytes_up": "Sent",
        "bytes_down": "Received",
        "auto_connect": "Auto-connect on start",
        "settings": "Settings",
        "about": "About",
        "about_text": "A simple SSH tunnel client built with Python and KivyMD. "
                      "It opens a local SOCKS5 proxy that routes traffic through "
                      "your SSH server.",
    },
    "ar": {
        "app_title": "إس إس إتش في بي إن",
        "app_subtitle": "عميل نفق SSH آمن",
        "server_section": "الخادم",
        "host": "المضيف / عنوان IP",
        "port": "المنفذ",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "local_port": "منفذ SOCKS المحلي",
        "save": "حفظ",
        "saved": "تم حفظ الإعدادات",
        "connect": "اتصال",
        "disconnect": "قطع الاتصال",
        "status": "الحالة",
        "status_disconnected": "غير متصل",
        "status_connecting": "جارٍ الاتصال…",
        "status_connected": "متصل",
        "status_error": "خطأ في الاتصال",
        "proxy_hint": "وكيل SOCKS5 يعمل على 127.0.0.1:{port}",
        "language": "اللغة",
        "english": "English",
        "arabic": "العربية",
        "fill_fields": "يرجى إدخال المضيف واسم المستخدم وكلمة المرور",
        "bytes_up": "المُرسَل",
        "bytes_down": "المُستقبَل",
        "auto_connect": "الاتصال التلقائي عند البدء",
        "settings": "الإعدادات",
        "about": "حول",
        "about_text": "عميل نفق SSH بسيط مبني باستخدام Python و KivyMD. "
                      "يفتح وكيل SOCKS5 محلي يوجّه حركة المرور عبر خادم SSH الخاص بك.",
    },
}

_current_language = "en"


def set_language(lang):
    """Set the active language ('en' or 'ar')."""
    global _current_language
    if lang in TRANSLATIONS:
        _current_language = lang


def get_language():
    """Return the active language code."""
    return _current_language


def is_rtl():
    """Return True if the active language is right-to-left."""
    return _current_language == "ar"


def tr(key, **kwargs):
    """Translate a key into the active language, with optional formatting."""
    text = TRANSLATIONS.get(_current_language, {}).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
