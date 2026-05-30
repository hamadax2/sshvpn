# -*- coding: utf-8 -*-
"""
SSH VPN — a simple bilingual (English / Arabic) SSH tunnel client
built with Python + KivyMD, packaged for Android with Buildozer.

It establishes an SSH connection and exposes a local SOCKS5 proxy
(see ssh_tunnel.py) that routes traffic through the SSH server.
"""

import os
import threading

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

import config_store
import localization as L10n
from ssh_tunnel import SSHTunnel

# Optional Arabic shaping (works if the libs are installed; degrades gracefully).
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def shape_ar(text):
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
except Exception:  # pragma: no cover
    def shape_ar(text):
        return text

FONT_NAME = "Roboto"


def _register_arabic_font():
    """Register a bundled Arabic-capable font if present."""
    global FONT_NAME
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "fonts", "Amiri-Regular.ttf"),
        os.path.join(here, "fonts", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(here, "fonts", "Cairo-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            LabelBase.register(name="Arabic", fn_regular=path)
            FONT_NAME = "Arabic"
            return


def display_text(text):
    """Apply Arabic shaping only when the active language is Arabic."""
    if L10n.is_rtl():
        return shape_ar(text)
    return text


class SectionCard(MDCard):
    """A simple rounded container card."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
            radius=[dp(16)] * 4,
            elevation=2,
            size_hint_y=None,
            **kwargs,
        )
        self.bind(minimum_height=self.setter("height"))


class SSHVPNApp(MDApp):
    status_key = StringProperty("status_disconnected")
    is_busy = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tunnel = SSHTunnel()
        self.config_data = config_store.load_config()
        self.fields = {}
        self.menu = None
        self._poll_event = None

    # ----- lifecycle -----

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.material_style = "M3"

        _register_arabic_font()
        L10n.set_language(self.config_data.get("language", "en"))

        self.root_layout = MDBoxLayout(orientation="vertical")
        self.toolbar = MDTopAppBar(
            title=display_text(L10n.tr("app_title")),
            elevation=0,
            right_action_items=[["translate", lambda x: self.open_language_menu(x)]],
        )
        self.root_layout.add_widget(self.toolbar)

        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(16),
            size_hint_y=None,
            adaptive_height=True,
        )
        scroll.add_widget(self.content)
        self.root_layout.add_widget(scroll)

        self._build_status_card()
        self._build_server_card()
        self._build_action_buttons()

        if self.config_data.get("auto_connect"):
            Clock.schedule_once(lambda dt: self.toggle_connection(), 0.8)

        return self.root_layout

    # ----- UI building -----

    def _label(self, key, **kw):
        lbl = MDLabel(
            text=display_text(L10n.tr(key)),
            font_name=FONT_NAME,
            halign="right" if L10n.is_rtl() else "left",
            **kw,
        )
        lbl._l10n_key = key
        return lbl

    def _build_status_card(self):
        self.status_card = SectionCard()
        self.status_title = self._label(
            "status", bold=True, font_style="H6", adaptive_height=True
        )
        self.status_value = MDLabel(
            text=display_text(L10n.tr(self.status_key)),
            font_name=FONT_NAME,
            font_style="H5",
            halign="center",
            adaptive_height=True,
        )
        self.proxy_label = MDLabel(
            text="",
            font_name=FONT_NAME,
            theme_text_color="Hint",
            halign="center",
            adaptive_height=True,
        )
        self.traffic_label = MDLabel(
            text="",
            font_name=FONT_NAME,
            theme_text_color="Hint",
            halign="center",
            adaptive_height=True,
        )
        self.status_card.add_widget(self.status_title)
        self.status_card.add_widget(self.status_value)
        self.status_card.add_widget(self.proxy_label)
        self.status_card.add_widget(self.traffic_label)
        self.content.add_widget(self.status_card)

    def _make_field(self, key, store_key, password=False, numeric=False):
        field = MDTextField(
            hint_text=display_text(L10n.tr(key)),
            text=str(self.config_data.get(store_key, "")),
            password=password,
            font_name=FONT_NAME,
            mode="rectangle",
            input_filter="int" if numeric else None,
        )
        field._l10n_key = key
        self.fields[store_key] = field
        return field

    def _build_server_card(self):
        self.server_card = SectionCard()
        self.server_title = self._label(
            "server_section", bold=True, font_style="H6", adaptive_height=True
        )
        self.server_card.add_widget(self.server_title)
        self.server_card.add_widget(self._make_field("host", "host"))
        self.server_card.add_widget(self._make_field("port", "port", numeric=True))
        self.server_card.add_widget(self._make_field("username", "username"))
        self.server_card.add_widget(
            self._make_field("password", "password", password=True)
        )
        self.server_card.add_widget(
            self._make_field("local_port", "local_port", numeric=True)
        )

        # auto-connect switch row
        row = MDBoxLayout(
            orientation="vertical", adaptive_height=True, spacing=dp(8)
        )
        self.auto_label = self._label("auto_connect", adaptive_height=True)
        self.auto_switch = MDSwitch(active=bool(self.config_data.get("auto_connect")))
        if L10n.is_rtl():
            row.add_widget(self.auto_switch)
            row.add_widget(self.auto_label)
        else:
            row.add_widget(self.auto_label)
            row.add_widget(self.auto_switch)
        self.server_card.add_widget(row)
        self.content.add_widget(self.server_card)

    def _build_action_buttons(self):
        btn_row = MDBoxLayout(
            orientation="vertical", adaptive_height=True, spacing=dp(12)
        )
        self.connect_btn = MDRaisedButton(
            text=display_text(L10n.tr("connect")),
            font_name=FONT_NAME,
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
            on_release=lambda x: self.toggle_connection(),
        )
        self.save_btn = MDFlatButton(
            text=display_text(L10n.tr("save")),
            font_name=FONT_NAME,
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
            on_release=lambda x: self.save_settings(),
        )
        btn_row.add_widget(self.connect_btn)
        btn_row.add_widget(self.save_btn)
        self.content.add_widget(btn_row)

    # ----- language -----

    def open_language_menu(self, caller):
        items = [
            {
                "viewclass": "OneLineListItem",
                "text": L10n.tr("english"),
                "on_release": lambda: self.set_language("en"),
            },
            {
                "viewclass": "OneLineListItem",
                "text": L10n.tr("arabic"),
                "on_release": lambda: self.set_language("ar"),
            },
        ]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=3)
        self.menu.open()

    def set_language(self, lang):
        if self.menu:
            self.menu.dismiss()
        L10n.set_language(lang)
        self.config_data["language"] = lang
        config_store.save_config(self.config_data)
        self.refresh_texts()

    def refresh_texts(self):
        """Re-apply translations to every widget after a language change."""
        rtl = L10n.is_rtl()
        self.toolbar.title = display_text(L10n.tr("app_title"))

        for widget in (
            self.status_title,
            self.server_title,
            self.auto_label,
        ):
            key = getattr(widget, "_l10n_key", None)
            if key:
                widget.text = display_text(L10n.tr(key))
                widget.halign = "right" if rtl else "left"

        for store_key, field in self.fields.items():
            field.hint_text = display_text(L10n.tr(field._l10n_key))

        self.connect_btn.text = display_text(
            L10n.tr("disconnect" if self.tunnel.is_connected else "connect")
        )
        self.save_btn.text = display_text(L10n.tr("save"))
        self.update_status_ui()

    # ----- settings -----

    def _collect_fields(self):
        for store_key, field in self.fields.items():
            self.config_data[store_key] = field.text.strip()
        self.config_data["auto_connect"] = bool(self.auto_switch.active)

    def save_settings(self):
        self._collect_fields()
        config_store.save_config(self.config_data)
        self.toast(L10n.tr("saved"))

    # ----- connection -----

    def toggle_connection(self):
        if self.is_busy:
            return
        if self.tunnel.is_connected:
            self.tunnel.disconnect()
            self._stop_polling()
            self.status_key = "status_disconnected"
            self.connect_btn.text = display_text(L10n.tr("connect"))
            self.update_status_ui()
            return

        self._collect_fields()
        if not (
            self.config_data["host"]
            and self.config_data["username"]
            and self.config_data["password"]
        ):
            self.toast(L10n.tr("fill_fields"))
            return

        config_store.save_config(self.config_data)
        self.is_busy = True
        self.status_key = "status_connecting"
        self.update_status_ui()
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            self.tunnel.connect(
                host=self.config_data["host"],
                port=self.config_data["port"] or "22",
                username=self.config_data["username"],
                password=self.config_data["password"],
                local_port=self.config_data["local_port"] or "1080",
            )
            Clock.schedule_once(lambda dt: self._on_connected())
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            Clock.schedule_once(lambda dt: self._on_error(message))

    def _on_connected(self):
        self.is_busy = False
        self.status_key = "status_connected"
        self.connect_btn.text = display_text(L10n.tr("disconnect"))
        self._start_polling()
        self.update_status_ui()

    def _on_error(self, message):
        self.is_busy = False
        self.status_key = "status_error"
        self.connect_btn.text = display_text(L10n.tr("connect"))
        self.update_status_ui()
        self.toast(message)

    # ----- status UI -----

    def update_status_ui(self):
        self.status_value.text = display_text(L10n.tr(self.status_key))
        if self.tunnel.is_connected:
            self.proxy_label.text = display_text(
                L10n.tr("proxy_hint", port=self.config_data.get("local_port", "1080"))
            )
            up = self._human_bytes(self.tunnel.bytes_up)
            down = self._human_bytes(self.tunnel.bytes_down)
            self.traffic_label.text = display_text(
                "{up}: {u}   {down}: {d}".format(
                    up=L10n.tr("bytes_up"),
                    u=up,
                    down=L10n.tr("bytes_down"),
                    d=down,
                )
            )
        else:
            self.proxy_label.text = ""
            self.traffic_label.text = ""

    def _start_polling(self):
        self._stop_polling()
        self._poll_event = Clock.schedule_interval(
            lambda dt: self.update_status_ui(), 1.0
        )

    def _stop_polling(self):
        if self._poll_event is not None:
            self._poll_event.cancel()
            self._poll_event = None

    @staticmethod
    def _human_bytes(num):
        for unit in ("B", "KB", "MB", "GB"):
            if num < 1024.0:
                return "%.1f %s" % (num, unit)
            num /= 1024.0
        return "%.1f TB" % num

    # ----- helpers -----

    def toast(self, message):
        dialog = MDDialog(
            text=display_text(message),
            buttons=[
                MDFlatButton(
                    text="OK",
                    font_name=FONT_NAME,
                    on_release=lambda x: dialog.dismiss(),
                )
            ],
        )
        dialog.open()

    def on_stop(self):
        try:
            self.tunnel.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    SSHVPNApp().run()
