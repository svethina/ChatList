"""Просмотр ответа в форматированном Markdown."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
)


def format_response_markdown(
    model_name: str,
    response_text: str,
    prompt_text: str = "",
) -> str:
    lines = [f"# {model_name}", ""]
    if prompt_text.strip():
        lines.extend(["## Промт", "", prompt_text.strip(), ""])
    lines.extend(["## Ответ", "", response_text])
    return "\n".join(lines)


class MarkdownViewerDialog(QDialog):
    def __init__(
        self,
        model_name: str,
        response_text: str,
        prompt_text: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ответ — {model_name}")
        self.resize(760, 580)

        layout = QVBoxLayout(self)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(
            format_response_markdown(model_name, response_text, prompt_text)
        )
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button:
            close_button.setText("Закрыть")
        layout.addWidget(buttons)


def open_markdown_viewer(
    parent,
    model_name: str,
    response_text: str,
    prompt_text: str = "",
) -> None:
    dialog = MarkdownViewerDialog(model_name, response_text, prompt_text, parent)
    dialog.exec()
