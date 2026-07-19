"""Вкладки управления моделями, историей и настройками."""

from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
import prompt_assistant
import ui_theme
from about_dialog import show_about_dialog
from markdown_viewer import open_markdown_viewer


PROVIDERS = ["openai", "openrouter", "deepseek", "groq", "huggingface"]
RESPONSE_MIN_ROW_HEIGHT = 100


class ModelEditDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        model_data: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактирование модели" if model_data else "Новая модель")
        self._model_id = model_data["id"] if model_data else None

        layout = QFormLayout(self)
        self.name_edit = QLineEdit(model_data["name"] if model_data else "")
        self.api_url_edit = QLineEdit(model_data["api_url"] if model_data else "")
        self.api_id_edit = QLineEdit(model_data["api_id"] if model_data else "")
        self.api_key_env_edit = QLineEdit(
            model_data["api_key_env"] if model_data else "OPENROUTER_API_KEY"
        )
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDERS)
        if model_data and model_data.get("provider"):
            index = self.provider_combo.findText(model_data["provider"])
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(bool(model_data["is_active"]) if model_data else True)

        layout.addRow("Имя", self.name_edit)
        layout.addRow("API URL", self.api_url_edit)
        layout.addRow("API ID модели", self.api_id_edit)
        layout.addRow("Переменная .env", self.api_key_env_edit)
        layout.addRow("Провайдер", self.provider_combo)
        layout.addRow("", self.active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "api_url": self.api_url_edit.text().strip(),
            "api_id": self.api_id_edit.text().strip(),
            "api_key_env": self.api_key_env_edit.text().strip(),
            "provider": self.provider_combo.currentText(),
            "is_active": self.active_check.isChecked(),
        }

    def accept(self) -> None:
        data = self.get_data()
        if not data["name"] or not data["api_url"]:
            QMessageBox.warning(self, "ChatList", "Укажите имя и API URL.")
            return
        if not data["api_id"] or not data["api_key_env"]:
            QMessageBox.warning(self, "ChatList", "Укажите API ID и переменную окружения.")
            return
        if not db.is_free_model(data["api_id"], data["provider"]):
            QMessageBox.warning(
                self,
                "ChatList",
                "Разрешены только бесплатные модели:\n"
                "• OpenRouter: api_id с суффиксом :free или openrouter/free\n"
                "• Hugging Face: provider = huggingface",
            )
            return
        super().accept()


class ModelsTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по имени, URL, провайдеру...")
        self.search_edit.textChanged.connect(self.reload)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "API URL", "API ID", "Переменная", "Активна"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_model)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self.edit_model)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_model)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.reload)
        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(refresh_btn)
        layout.addLayout(buttons)

        self.reload()

    def reload(self) -> None:
        query = self.search_edit.text().strip()
        if query:
            rows = [
                r
                for r in db.search_models(query)
                if db.is_free_model(r["api_id"], r.get("provider"))
            ]
        else:
            rows = [
                r
                for r in db.list_models(active_only=False)
                if db.is_free_model(r["api_id"], r.get("provider"))
            ]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["id"]),
                row["name"],
                row["api_url"],
                row["api_id"],
                row["api_key_env"],
                "Да" if row["is_active"] else "Нет",
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)
        self.table.setSortingEnabled(True)

    def _selected_model_id(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        id_item = self.table.item(selected[0].row(), 0)
        return int(id_item.text()) if id_item else None

    def add_model(self) -> None:
        dialog = ModelEditDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            db.add_model(
                data["name"],
                data["api_url"],
                data["api_id"],
                data["api_key_env"],
                data["is_active"],
                data["provider"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return
        self.reload()
        self.changed.emit()

    def edit_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "ChatList", "Выберите модель.")
            return
        model_data = db.get_model(model_id)
        if not model_data:
            return
        dialog = ModelEditDialog(self, model_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            db.update_model(model_id, **data)
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return
        self.reload()
        self.changed.emit()

    def delete_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "ChatList", "Выберите модель.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            "Удалить выбранную модель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            db.delete_model(model_id)
        except Exception as exc:
            QMessageBox.critical(self, "ChatList", f"Не удалось удалить: {exc}")
            return
        self.reload()
        self.changed.emit()


class PromptEditDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        prompt_data: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактирование промта" if prompt_data else "Новый промт")

        layout = QFormLayout(self)
        self.prompt_edit = QTextEdit(prompt_data["prompt"] if prompt_data else "")
        self.prompt_edit.setMinimumHeight(140)
        self.tags_edit = QLineEdit((prompt_data or {}).get("tags") or "")

        layout.addRow("Промт", self.prompt_edit)
        layout.addRow("Теги", self.tags_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict[str, str]:
        return {
            "prompt": self.prompt_edit.toPlainText().strip(),
            "tags": self.tags_edit.text().strip(),
        }

    def accept(self) -> None:
        data = self.get_data()
        if not data["prompt"]:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return
        super().accept()


class PromptsTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по тексту промта и тегам...")
        self.search_edit.textChanged.connect(self.reload)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_prompt)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self.edit_prompt)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_prompt)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.reload)
        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(refresh_btn)
        layout.addLayout(buttons)

        self.reload()

    def reload(self) -> None:
        query = self.search_edit.text().strip()
        rows = db.search_prompts(query) if query else db.list_prompts()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row["id"]),
                row["created_at"],
                row["prompt"],
                row.get("tags") or "",
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_index == 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    )
                self.table.setItem(row_index, col_index, item)
        self.table.setSortingEnabled(True)
        self.table.resizeRowsToContents()

    def _selected_prompt_id(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        id_item = self.table.item(selected[0].row(), 0)
        return int(id_item.text()) if id_item else None

    def add_prompt(self) -> None:
        dialog = PromptEditDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        db.add_prompt(data["prompt"], data["tags"] or None)
        self.reload()
        self.changed.emit()

    def edit_prompt(self) -> None:
        prompt_id = self._selected_prompt_id()
        if prompt_id is None:
            QMessageBox.information(self, "ChatList", "Выберите промт.")
            return
        prompt_data = db.get_prompt(prompt_id)
        if not prompt_data:
            return
        dialog = PromptEditDialog(self, prompt_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        db.update_prompt(prompt_id, prompt=data["prompt"], tags=data["tags"])
        self.reload()
        self.changed.emit()

    def delete_prompt(self) -> None:
        prompt_id = self._selected_prompt_id()
        if prompt_id is None:
            QMessageBox.information(self, "ChatList", "Выберите промт.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            "Удалить выбранный промт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            db.delete_prompt(prompt_id)
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "ChatList",
                "Нельзя удалить промт, у которого уже есть сохранённые результаты.",
            )
            return
        except Exception as exc:
            QMessageBox.critical(self, "ChatList", f"Не удалось удалить: {exc}")
            return
        self.reload()
        self.changed.emit()


class HistoryTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по промту, модели, ответу...")
        self.search_edit.textChanged.connect(self.reload)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Дата", "Модель", "Промт", "Ответ", "ID", "Открыть"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(RESPONSE_MIN_ROW_HEIGHT)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.reload)
        layout.addWidget(refresh_btn)

        self.reload()

    def reload(self) -> None:
        query = self.search_edit.text().strip()
        rows = db.search_results(query) if query else db.list_results()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            prompt_preview = row["prompt_text"].replace("\n", " ")
            if len(prompt_preview) > 80:
                prompt_preview = prompt_preview[:77] + "..."
            values = [
                row["created_at"],
                row["model_name"],
                prompt_preview,
                row["response_text"],
                str(row["id"]),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_index in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    )
                if col_index == 2:
                    item.setData(Qt.ItemDataRole.UserRole, row["prompt_text"])
                self.table.setItem(row_index, col_index, item)

            open_btn = QPushButton("Открыть")
            open_btn.clicked.connect(
                lambda _checked=False, row=row_index: self.on_open_response(row)
            )
            self.table.setCellWidget(row_index, 5, open_btn)
        self.table.setSortingEnabled(True)
        self.table.resizeRowsToContents()
        for row_index in range(len(rows)):
            if self.table.rowHeight(row_index) < RESPONSE_MIN_ROW_HEIGHT:
                self.table.setRowHeight(row_index, RESPONSE_MIN_ROW_HEIGHT)

    def on_open_response(self, row_index: int) -> None:
        model_item = self.table.item(row_index, 1)
        prompt_item = self.table.item(row_index, 2)
        response_item = self.table.item(row_index, 3)
        if not model_item or not response_item:
            return
        prompt_text = ""
        if prompt_item:
            prompt_text = prompt_item.data(Qt.ItemDataRole.UserRole) or prompt_item.text()
        open_markdown_viewer(
            self,
            model_item.text(),
            response_item.text(),
            str(prompt_text),
        )


class SettingsTab(QWidget):
    saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)

        self.timeout_edit = QLineEdit()
        self.db_path_edit = QLineEdit()
        self.log_requests_check = QCheckBox("Логировать HTTP-запросы в файл")
        self.log_file_edit = QLineEdit()
        self.use_proxy_check = QCheckBox("Использовать системный прокси (HTTP/SOCKS)")
        self.improve_model_combo = QComboBox()
        self.theme_combo = QComboBox()
        self.font_size_combo = QComboBox()

        layout.addRow("Таймаут запроса (сек)", self.timeout_edit)
        layout.addRow("Путь к БД", self.db_path_edit)
        layout.addRow("", self.log_requests_check)
        layout.addRow("Файл логов", self.log_file_edit)
        layout.addRow("", self.use_proxy_check)
        layout.addRow("Модель для улучшения промтов", self.improve_model_combo)
        layout.addRow("Тема интерфейса", self.theme_combo)
        layout.addRow("Размер шрифта", self.font_size_combo)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

        about_btn = QPushButton("О программе")
        about_btn.clicked.connect(self.show_about)
        layout.addRow(about_btn)

        note = QLabel("Изменение пути к БД вступит в силу после перезапуска.")
        note.setWordWrap(True)
        layout.addRow(note)

        for theme_id, theme_label in ui_theme.THEMES.items():
            self.theme_combo.addItem(theme_label, theme_id)
        for size in range(ui_theme.MIN_FONT_SIZE, ui_theme.MAX_FONT_SIZE + 1):
            self.font_size_combo.addItem(str(size), str(size))

        self.reload()

    def reload(self) -> None:
        self.timeout_edit.setText(db.get_setting("request_timeout") or "60")
        self.db_path_edit.setText(db.get_setting("db_path") or "chatlist.db")
        self.log_requests_check.setChecked((db.get_setting("log_requests") or "0") == "1")
        self.log_file_edit.setText(db.get_setting("log_file") or "chatlist.log")
        self.use_proxy_check.setChecked((db.get_setting("use_system_proxy") or "0") == "1")
        self._reload_improve_model_combo()
        self._reload_appearance_controls()

    def _reload_appearance_controls(self) -> None:
        theme = db.get_setting("ui_theme") or ui_theme.THEME_LIGHT
        theme_index = self.theme_combo.findData(theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)

        font_size = db.get_setting("ui_font_size") or str(ui_theme.DEFAULT_FONT_SIZE)
        font_index = self.font_size_combo.findData(font_size)
        if font_index >= 0:
            self.font_size_combo.setCurrentIndex(font_index)

    def _reload_improve_model_combo(self) -> None:
        saved_id = db.get_setting("improve_prompt_model_id") or ""
        default_model = prompt_assistant.get_default_assistant_model()
        if not saved_id and default_model is not None:
            saved_id = str(default_model.id)

        self.improve_model_combo.blockSignals(True)
        self.improve_model_combo.clear()
        self.improve_model_combo.addItem("— не выбрана —", "")
        selected_index = 0
        for index, row in enumerate(db.list_models(active_only=True), start=1):
            self.improve_model_combo.addItem(row["name"], str(row["id"]))
            if saved_id and str(row["id"]) == saved_id:
                selected_index = index
        self.improve_model_combo.setCurrentIndex(selected_index)
        self.improve_model_combo.blockSignals(False)

    def save(self) -> None:
        timeout = self.timeout_edit.text().strip()
        if not timeout.isdigit() or int(timeout) <= 0:
            QMessageBox.warning(self, "ChatList", "Таймаут должен быть положительным числом.")
            return
        db_path = self.db_path_edit.text().strip()
        if not db_path:
            QMessageBox.warning(self, "ChatList", "Укажите путь к базе данных.")
            return
        log_file = self.log_file_edit.text().strip()
        if not log_file:
            QMessageBox.warning(self, "ChatList", "Укажите файл логов.")
            return

        db.set_setting("request_timeout", timeout)
        db.set_setting("db_path", db_path)
        db.set_setting("log_requests", "1" if self.log_requests_check.isChecked() else "0")
        db.set_setting("log_file", log_file)
        db.set_setting(
            "use_system_proxy", "1" if self.use_proxy_check.isChecked() else "0"
        )
        improve_model_id = self.improve_model_combo.currentData() or ""
        db.set_setting("improve_prompt_model_id", str(improve_model_id))
        db.set_setting("ui_theme", self.theme_combo.currentData() or ui_theme.THEME_LIGHT)
        db.set_setting("ui_font_size", self.font_size_combo.currentData() or str(ui_theme.DEFAULT_FONT_SIZE))
        QMessageBox.information(self, "ChatList", "Настройки сохранены.")
        self.saved.emit()

    def show_about(self) -> None:
        show_about_dialog(self)
