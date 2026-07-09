"""Тема оформления и размер шрифта интерфейса."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QStyleFactory

import db

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEMES = {
    THEME_LIGHT: "Светлая",
    THEME_DARK: "Тёмная",
}

DEFAULT_FONT_SIZE = 10
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 20


def get_ui_theme() -> str:
    theme = (db.get_setting("ui_theme") or THEME_LIGHT).strip().lower()
    return theme if theme in THEMES else THEME_LIGHT


def get_ui_font_size() -> int:
    raw = db.get_setting("ui_font_size") or str(DEFAULT_FONT_SIZE)
    try:
        size = int(raw)
    except ValueError:
        size = DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 32))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 32))
    palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.Button, QColor(58, 58, 62))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 80))
    palette.setColor(QPalette.ColorRole.Link, QColor(120, 170, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(64, 128, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return palette


def _light_palette(app: QApplication) -> QPalette:
    return app.style().standardPalette()


def apply_ui_settings(
    app: QApplication,
    theme: str | None = None,
    font_size: int | None = None,
) -> None:
    selected_theme = theme or get_ui_theme()
    selected_font_size = font_size or get_ui_font_size()

    app.setStyle(QStyleFactory.create("Fusion"))
    if selected_theme == THEME_DARK:
        app.setPalette(_dark_palette())
    else:
        app.setPalette(_light_palette(app))

    font = QFont(app.font())
    font.setPointSize(selected_font_size)
    app.setFont(font)
