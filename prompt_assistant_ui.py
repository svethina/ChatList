"""Диалог результатов AI-ассистента для улучшения промтов."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from prompt_assistant import PromptImprovementResult

ADAPTATION_LABELS = {
    "code": "Код",
    "analysis": "Анализ",
    "creative": "Креатив",
}


class ImprovePromptDialog(QDialog):
    variant_selected = pyqtSignal(str)

    def __init__(
        self,
        result: PromptImprovementResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Улучшение промта")
        self.resize(760, 680)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        content_layout.addWidget(QLabel("Исходный промт"))
        original_edit = QTextEdit()
        original_edit.setReadOnly(True)
        original_edit.setPlainText(result.original)
        original_edit.setMinimumHeight(80)
        content_layout.addWidget(original_edit)

        content_layout.addLayout(self._variant_block("Улучшенный", result.improved))

        for index, alternative in enumerate(result.alternatives, start=1):
            content_layout.addLayout(
                self._variant_block(f"Альтернатива {index}", alternative)
            )

        for key, label in ADAPTATION_LABELS.items():
            text = result.adaptations.get(key, "")
            if text:
                content_layout.addLayout(
                    self._variant_block(f"Адаптация: {label}", text)
                )

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText("Закрыть")
        layout.addWidget(buttons)

    def _variant_block(self, title: str, text: str) -> QVBoxLayout:
        block = QVBoxLayout()
        block.addWidget(QLabel(title))

        line = QHBoxLayout()
        edit = QTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(text)
        edit.setMinimumHeight(70)
        line.addWidget(edit, 1)

        apply_btn = QPushButton("Подставить")
        apply_btn.clicked.connect(lambda: self._apply_variant(text))
        line.addWidget(apply_btn)

        block.addLayout(line)
        return block

    def _apply_variant(self, text: str) -> None:
        self.variant_selected.emit(text)
        self.accept()
