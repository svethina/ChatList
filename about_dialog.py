"""Диалог «О программе»."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from version import __version__

ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"

APP_NAME = "ChatList"
APP_DESCRIPTION = (
    "ChatList — приложение для отправки одного промта в несколько нейросетей "
    "и сравнения их ответов."
)
APP_DETAILS = (
    "• Сохранение промтов, моделей и результатов в SQLite\n"
    "• Экспорт ответов в Markdown и JSON\n"
    "• AI-ассистент для улучшения промтов\n"
    "• Настройка темы и размера шрифта"
)
APP_STACK = "Python 3.11+ · PyQt6 · SQLite · httpx"


def _dialog_icon() -> QIcon | None:
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))
    return None


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"О программе {APP_NAME}")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        icon_label = QLabel()
        icon = _dialog_icon()
        if icon is not None and not icon.isNull():
            pixmap = icon.pixmap(64, 64)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Версия {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        description = QLabel(APP_DESCRIPTION)
        description.setWordWrap(True)
        layout.addWidget(description)

        details = QLabel(APP_DETAILS)
        details.setWordWrap(True)
        layout.addWidget(details)

        stack = QLabel(APP_STACK)
        stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(stack)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Закрыть")
        layout.addWidget(buttons)


def show_about_dialog(parent=None) -> None:
    AboutDialog(parent).exec()
