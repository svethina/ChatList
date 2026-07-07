"""Главное окно ChatList."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import db
import export_utils
import models as app_models
from markdown_viewer import open_markdown_viewer
from tabs import HistoryTab, ModelsTab, SettingsTab

RESPONSE_MIN_ROW_HEIGHT = 100


class SendWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, prompt_text: str, active_models: list[app_models.Model]) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.active_models = active_models

    def run(self) -> None:
        try:
            results = app_models.run_prompt(self.prompt_text, self.active_models)
            self.finished.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class PromptTab(QWidget):
    results_saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: SendWorker | None = None
        self._current_prompt_id: int | None = None
        self._loading_saved_prompt = False

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Сохранённые промты"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.currentIndexChanged.connect(self.on_saved_prompt_selected)
        layout.addWidget(self.prompt_combo)

        layout.addWidget(QLabel("Новый промт"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса...")
        self.prompt_edit.setMinimumHeight(120)
        layout.addWidget(self.prompt_edit)

        layout.addWidget(QLabel("Теги"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("тег1, тег2")
        layout.addWidget(self.tags_edit)

        buttons_row = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.on_send)
        buttons_row.addWidget(self.send_button)

        self.save_button = QPushButton("Сохранить выбранные")
        self.save_button.clicked.connect(self.on_save)
        self.save_button.setEnabled(False)
        buttons_row.addWidget(self.save_button)

        export_md_btn = QPushButton("Экспорт Markdown")
        export_md_btn.clicked.connect(self.on_export_markdown)
        buttons_row.addWidget(export_md_btn)

        export_json_btn = QPushButton("Экспорт JSON")
        export_json_btn.clicked.connect(self.on_export_json)
        buttons_row.addWidget(export_json_btn)
        layout.addLayout(buttons_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Результаты"))
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(
            ["Модель", "Ответ", "Выбрать", "Открыть"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setWordWrap(True)
        self.results_table.verticalHeader().setDefaultSectionSize(RESPONSE_MIN_ROW_HEIGHT)
        self.results_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setMinimumHeight(300)
        layout.addWidget(self.results_table)

        self.status_label = QLabel("Готово")
        layout.addWidget(self.status_label)

        self.reload_saved_prompts()

    def reload_saved_prompts(self) -> None:
        self._loading_saved_prompt = True
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— новый промт —", None)
        for prompt in app_models.load_saved_prompts():
            label = prompt.text.replace("\n", " ")
            if len(label) > 80:
                label = label[:77] + "..."
            if prompt.tags:
                label = f"{label} [{prompt.tags}]"
            self.prompt_combo.addItem(label, prompt.id)
        self.prompt_combo.blockSignals(False)
        self._loading_saved_prompt = False

    def on_saved_prompt_selected(self, index: int) -> None:
        if self._loading_saved_prompt or index < 0:
            return
        prompt_id = self.prompt_combo.itemData(index)
        if prompt_id is None:
            self._current_prompt_id = None
            return
        row = db.get_prompt(int(prompt_id))
        if not row:
            return
        self._loading_saved_prompt = True
        self.prompt_edit.setPlainText(row["prompt"])
        self.tags_edit.setText(row.get("tags") or "")
        self._loading_saved_prompt = False
        self._current_prompt_id = int(prompt_id)

    def on_send(self) -> None:
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return

        active_models = app_models.load_active_models()
        if not active_models:
            QMessageBox.warning(
                self,
                "ChatList",
                "Нет активных моделей. Включите модели на вкладке «Модели».",
            )
            return

        app_models.clear_temp_results()
        self.clear_results_table()
        self.save_button.setEnabled(False)

        combo_id = self.prompt_combo.currentData()
        if combo_id is not None:
            self._current_prompt_id = int(combo_id)
        else:
            prompt = app_models.Prompt(
                id=None,
                text=prompt_text,
                tags=self.tags_edit.text().strip(),
            )
            self._current_prompt_id = prompt.save()
            self.reload_saved_prompts()

        app_models.set_current_prompt_id(self._current_prompt_id)
        self.set_loading(True)

        self._worker = SendWorker(prompt_text, active_models)
        self._worker.finished.connect(self.on_send_finished)
        self._worker.failed.connect(self.on_send_failed)
        self._worker.start()

    def on_send_finished(self, results: list[app_models.TempResult]) -> None:
        self.set_loading(False)
        self.populate_results_table(results)
        if results:
            self.save_button.setEnabled(True)
            self.status_label.setText(f"Получено ответов: {len(results)}")
        else:
            self.status_label.setText("Ответы не получены")

    def on_send_failed(self, message: str) -> None:
        self.set_loading(False)
        QMessageBox.critical(self, "ChatList", f"Ошибка отправки: {message}")
        self.status_label.setText("Ошибка отправки")

    def on_save(self) -> None:
        if self._current_prompt_id is None:
            QMessageBox.warning(self, "ChatList", "Сначала отправьте промт.")
            return

        temp_results = self.read_results_from_table()
        selected_count = sum(1 for item in temp_results if item.selected)
        if selected_count == 0:
            QMessageBox.information(self, "ChatList", "Отметьте хотя бы один результат.")
            return

        saved = app_models.save_selected_results(self._current_prompt_id, temp_results)
        self.clear_results_table()
        self.save_button.setEnabled(False)
        self.status_label.setText(f"Сохранено результатов: {saved}")
        self.results_saved.emit()

    def on_export_markdown(self) -> None:
        self._export_file("Markdown (*.md)", ".md", export_utils.export_to_markdown)

    def on_export_json(self) -> None:
        self._export_file("JSON (*.json)", ".json", export_utils.export_to_json)

    def _export_file(self, filter_str: str, suffix: str, exporter) -> None:
        results = self._results_for_export()
        if not results:
            QMessageBox.information(self, "ChatList", "Нет результатов для экспорта.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", filter_str)
        if not path:
            return
        if not path.endswith(suffix):
            path += suffix
        content = exporter(results, self.prompt_edit.toPlainText().strip())
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        QMessageBox.information(self, "ChatList", f"Файл сохранён: {path}")

    def _results_for_export(self) -> list[app_models.TempResult]:
        results = self.read_results_from_table()
        selected = [item for item in results if item.selected]
        return selected if selected else results

    def set_loading(self, loading: bool) -> None:
        self.progress.setVisible(loading)
        self.send_button.setEnabled(not loading)
        self.save_button.setEnabled(not loading and self.results_table.rowCount() > 0)
        if loading:
            self.status_label.setText("Отправка запросов...")

    def clear_results_table(self) -> None:
        self.results_table.setRowCount(0)

    def populate_results_table(self, results: list[app_models.TempResult]) -> None:
        self.results_table.setRowCount(len(results))
        for row_index, item in enumerate(results):
            name_item = QTableWidgetItem(item.model_name)
            name_item.setData(Qt.ItemDataRole.UserRole, item.model_id)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            self.results_table.setItem(row_index, 0, name_item)

            response_item = QTableWidgetItem(item.response_text)
            response_item.setFlags(response_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            response_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            self.results_table.setItem(row_index, 1, response_item)

            select_item = QTableWidgetItem()
            select_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            select_item.setCheckState(
                Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked
            )
            self.results_table.setItem(row_index, 2, select_item)

            open_btn = QPushButton("Открыть")
            open_btn.clicked.connect(
                lambda _checked=False, row=row_index: self.on_open_response(row)
            )
            self.results_table.setCellWidget(row_index, 3, open_btn)

        self.results_table.resizeRowsToContents()
        for row_index in range(len(results)):
            if self.results_table.rowHeight(row_index) < RESPONSE_MIN_ROW_HEIGHT:
                self.results_table.setRowHeight(row_index, RESPONSE_MIN_ROW_HEIGHT)

    def read_results_from_table(self) -> list[app_models.TempResult]:
        results: list[app_models.TempResult] = []
        for row_index in range(self.results_table.rowCount()):
            name_item = self.results_table.item(row_index, 0)
            response_item = self.results_table.item(row_index, 1)
            select_item = self.results_table.item(row_index, 2)
            if not name_item or not response_item or not select_item:
                continue
            model_id = name_item.data(Qt.ItemDataRole.UserRole)
            if model_id is None:
                model_id = 0
            results.append(
                app_models.TempResult(
                    model_id=int(model_id),
                    model_name=name_item.text(),
                    response_text=response_item.text(),
                    selected=select_item.checkState() == Qt.CheckState.Checked,
                )
            )
        return results

    def on_open_response(self, row_index: int) -> None:
        name_item = self.results_table.item(row_index, 0)
        response_item = self.results_table.item(row_index, 1)
        if not name_item or not response_item:
            return
        open_markdown_viewer(
            self,
            name_item.text(),
            response_item.text(),
            self.prompt_edit.toPlainText().strip(),
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.resize(1000, 760)

        tabs = QTabWidget()
        self.prompt_tab = PromptTab()
        self.models_tab = ModelsTab()
        self.history_tab = HistoryTab()
        self.settings_tab = SettingsTab()

        tabs.addTab(self.prompt_tab, "Запрос")
        tabs.addTab(self.models_tab, "Модели")
        tabs.addTab(self.history_tab, "История")
        tabs.addTab(self.settings_tab, "Настройки")
        self.setCentralWidget(tabs)

        self.models_tab.changed.connect(self.prompt_tab.reload_saved_prompts)
        self.prompt_tab.results_saved.connect(self.history_tab.reload)


def main() -> None:
    db.init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
