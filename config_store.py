# -*- coding: utf-8 -*-
"""
Lightweight JSON-based settings storage.

On Android, files written to the app's private directory persist between runs.
We use a per-user config file in the platform's app storage directory.
"""

import json
import os

DEFAULTS = {
    "host": "",
    "port": "22",
    "username": "",
    "password": "",
    "local_port": "1080",
    "language": "en",
    "auto_connect": False,
}


def _config_dir():
    """Return a writable directory for storing the config file."""
    # Try Kivy's app storage path first (works on Android).
    try:
        from kivy.app import App

        app = App.get_running_app()
        if app is not None and app.user_data_dir:
            return app.user_data_dir
    except Exception:
        pass
    # Fallback to the user's home directory.
    base = os.path.expanduser("~")
    path = os.path.join(base, ".ssh_vpn")
    os.makedirs(path, exist_ok=True)
    return path


def _config_path():
    return os.path.join(_config_dir(), "ssh_vpn_config.json")


def load_config():
    """Load settings, merged over defaults."""
    data = dict(DEFAULTS)
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            saved = json.load(f)
            if isinstance(saved, dict):
                data.update({k: saved[k] for k in saved if k in DEFAULTS})
    except (FileNotFoundError, ValueError, OSError):
        pass
    return data


def save_config(config):
    """Persist settings to disk."""
    data = dict(DEFAULTS)
    data.update({k: config[k] for k in config if k in DEFAULTS})
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
