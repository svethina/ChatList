"""Тестовый просмотрщик SQLite с пагинацией и CRUD."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
)

PAGE_SIZE = 20


def quote_ident(name: str) -> str:
    """Безопасно экранирует идентификатор SQLite."""
    return f'"{name.replace("\"", "\"\"")}"'


@dataclass
class ColumnInfo:
    name: str
    col_type: str
    is_pk: bool


class RowEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        columns: list[ColumnInfo],
        values: dict[str, object] | None = None,
        title: str = "Редактирование записи",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._edits: dict[str, QLineEdit] = {}
        self._columns = columns

        form = QFormLayout(self)
        for col in columns:
            edit = QLineEdit()
            if values and col.name in values and values[col.name] is not None:
                edit.setText(str(values[col.name]))
            self._edits[col.name] = edit
            form.addRow(f"{col.name} ({col.col_type or 'TEXT'})", edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_values(self) -> dict[str, str | None]:
        result: dict[str, str | None] = {}
        for col in self._columns:
            text = self._edits[col.name].text()
            result[col.name] = text if text != "" else None
        return result


class DbViewerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SQLite Test DB Viewer")
        self.resize(1100, 700)

        self.db_path: str | None = None
        self.conn: sqlite3.Connection | None = None
        self.current_table: str | None = None
        self.columns: list[ColumnInfo] = []
        self.pk_columns: list[str] = []
        self.page = 0
        self.total_rows = 0
        self.has_rowid = True

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top_row = QHBoxLayout()
        self.open_file_btn = QPushButton("Выбрать SQLite файл")
        self.open_file_btn.clicked.connect(self.choose_db_file)
        top_row.addWidget(self.open_file_btn)

        self.db_label = QLabel("Файл не выбран")
        self.db_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top_row.addWidget(self.db_label, 1)
        layout.addLayout(top_row)

        middle_row = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Таблицы"))
        self.tables_list = QListWidget()
        left_col.addWidget(self.tables_list, 1)
        self.open_table_btn = QPushButton("Открыть")
        self.open_table_btn.clicked.connect(self.open_selected_table)
        left_col.addWidget(self.open_table_btn)
        middle_row.addLayout(left_col, 1)

        right_col = QVBoxLayout()
        self.info_label = QLabel("Выберите файл и таблицу.")
        right_col.addWidget(self.info_label)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        right_col.addWidget(self.table, 1)

        pagination_row = QHBoxLayout()
        self.prev_btn = QPushButton("Назад")
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn = QPushButton("Вперед")
        self.next_btn.clicked.connect(self.next_page)
        self.page_label = QLabel("Страница: 0/0")
        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.next_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addStretch(1)
        right_col.addLayout(pagination_row)

        crud_row = QHBoxLayout()
        self.add_btn = QPushButton("Создать")
        self.add_btn.clicked.connect(self.create_row)
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self.update_row)
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_row)
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.reload_table_data)
        crud_row.addWidget(self.add_btn)
        crud_row.addWidget(self.edit_btn)
        crud_row.addWidget(self.delete_btn)
        crud_row.addWidget(self.refresh_btn)
        crud_row.addStretch(1)
        right_col.addLayout(crud_row)

        middle_row.addLayout(right_col, 4)
        layout.addLayout(middle_row, 1)

        self.set_actions_enabled(False)

    def set_actions_enabled(self, enabled: bool) -> None:
        for btn in (
            self.open_table_btn,
            self.prev_btn,
            self.next_btn,
            self.add_btn,
            self.edit_btn,
            self.delete_btn,
            self.refresh_btn,
        ):
            btn.setEnabled(enabled)

    def choose_db_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите SQLite файл",
            "",
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if not path:
            return
        self.connect_db(path)

    def connect_db(self, path: str) -> None:
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            conn.execute("SELECT 1")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть БД:\n{exc}")
            return

        if self.conn:
            self.conn.close()
        self.conn = conn
        self.db_path = path
        self.db_label.setText(path)
        self.current_table = None
        self.columns = []
        self.pk_columns = []
        self.page = 0
        self.total_rows = 0
        self.load_tables()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.info_label.setText("Выберите таблицу и нажмите «Открыть».")

    def load_tables(self) -> None:
        if not self.conn:
            return
        rows = self.conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        self.tables_list.clear()
        for row in rows:
            self.tables_list.addItem(str(row["name"]))
        self.set_actions_enabled(bool(rows))

    def open_selected_table(self) -> None:
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Внимание", "Выберите таблицу.")
            return
        self.current_table = item.text()
        self.page = 0
        self.read_table_schema()
        self.reload_table_data()

    def read_table_schema(self) -> None:
        if not self.conn or not self.current_table:
            return
        rows = self.conn.execute(
            f"PRAGMA table_info({quote_ident(self.current_table)})"
        ).fetchall()
        self.columns = [
            ColumnInfo(name=row["name"], col_type=row["type"], is_pk=bool(row["pk"]))
            for row in rows
        ]
        self.pk_columns = [c.name for c in self.columns if c.is_pk]

    def reload_table_data(self) -> None:
        if not self.conn or not self.current_table:
            return
        table_name = quote_ident(self.current_table)
        try:
            self.total_rows = int(
                self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            )
            offset = self.page * PAGE_SIZE
            try:
                rows = self.conn.execute(
                    f"SELECT rowid AS __rowid__, * FROM {table_name} LIMIT ? OFFSET ?",
                    (PAGE_SIZE, offset),
                ).fetchall()
                self.has_rowid = True
            except sqlite3.OperationalError:
                rows = self.conn.execute(
                    f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
                    (PAGE_SIZE, offset),
                ).fetchall()
                self.has_rowid = False
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{exc}")
            return

        display_columns = [c.name for c in self.columns]
        self.table.setColumnCount(len(display_columns))
        self.table.setHorizontalHeaderLabels(display_columns)
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            if self.has_rowid:
                self.table.setVerticalHeaderItem(
                    row_index, QTableWidgetItem(str(row["__rowid__"]))
                )
            for col_index, col_name in enumerate(display_columns):
                value = row[col_name]
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()
        total_pages = max(1, (self.total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label.setText(f"Страница: {self.page + 1}/{total_pages}")
        self.prev_btn.setEnabled(self.page > 0)
        self.next_btn.setEnabled((self.page + 1) * PAGE_SIZE < self.total_rows)
        self.info_label.setText(
            f"Таблица: {self.current_table} | Записей: {self.total_rows} | PK: "
            + (", ".join(self.pk_columns) if self.pk_columns else "нет")
        )

    def prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.reload_table_data()

    def next_page(self) -> None:
        if (self.page + 1) * PAGE_SIZE < self.total_rows:
            self.page += 1
            self.reload_table_data()

    def _selected_row_values(self) -> dict[str, str]:
        row_index = self.table.currentRow()
        if row_index < 0:
            return {}
        values: dict[str, str] = {}
        for col_index, col in enumerate(self.columns):
            item = self.table.item(row_index, col_index)
            values[col.name] = item.text() if item else ""
        return values

    def _where_for_selected(self) -> tuple[str, list[object]] | None:
        row_index = self.table.currentRow()
        if row_index < 0:
            return None
        if self.pk_columns:
            clauses: list[str] = []
            params: list[object] = []
            for pk_name in self.pk_columns:
                col_index = next(i for i, c in enumerate(self.columns) if c.name == pk_name)
                value_item = self.table.item(row_index, col_index)
                value = value_item.text() if value_item else None
                clauses.append(f"{quote_ident(pk_name)} IS ?")
                params.append(value if value != "" else None)
            return " AND ".join(clauses), params

        if self.has_rowid:
            header_item = self.table.verticalHeaderItem(row_index)
            if header_item:
                return "rowid = ?", [header_item.text()]
        return None

    def create_row(self) -> None:
        if not self.conn or not self.current_table:
            return
        dialog = RowEditorDialog(self, self.columns, title="Создание записи")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.get_values()
        insert_columns: list[str] = []
        params: list[object] = []
        for col in self.columns:
            val = values.get(col.name)
            if col.is_pk and val is None:
                continue
            insert_columns.append(quote_ident(col.name))
            params.append(val)

        if not insert_columns:
            QMessageBox.warning(self, "Ошибка", "Нет полей для вставки.")
            return

        placeholders = ", ".join("?" for _ in insert_columns)
        sql = (
            f"INSERT INTO {quote_ident(self.current_table)} "
            f"({', '.join(insert_columns)}) VALUES ({placeholders})"
        )
        try:
            self.conn.execute(sql, params)
            self.conn.commit()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать запись:\n{exc}")
            return
        self.reload_table_data()

    def update_row(self) -> None:
        if not self.conn or not self.current_table:
            return
        current_values = self._selected_row_values()
        if not current_values:
            QMessageBox.information(self, "Внимание", "Выберите строку для изменения.")
            return
        where_clause = self._where_for_selected()
        if where_clause is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Невозможно определить запись (нет PK/rowid).",
            )
            return

        dialog = RowEditorDialog(
            self, self.columns, values=current_values, title="Изменение записи"
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_values = dialog.get_values()

        set_parts: list[str] = []
        params: list[object] = []
        for col in self.columns:
            if col.name in self.pk_columns:
                continue
            set_parts.append(f"{quote_ident(col.name)} = ?")
            params.append(new_values.get(col.name))

        if not set_parts:
            QMessageBox.warning(self, "Ошибка", "Нет изменяемых полей.")
            return

        where_sql, where_params = where_clause
        sql = (
            f"UPDATE {quote_ident(self.current_table)} "
            f"SET {', '.join(set_parts)} WHERE {where_sql}"
        )
        try:
            self.conn.execute(sql, params + where_params)
            self.conn.commit()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить запись:\n{exc}")
            return
        self.reload_table_data()

    def delete_row(self) -> None:
        if not self.conn or not self.current_table:
            return
        where_clause = self._where_for_selected()
        if where_clause is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Невозможно определить запись (нет PK/rowid).",
            )
            return
        answer = QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить выбранную запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        where_sql, where_params = where_clause
        sql = f"DELETE FROM {quote_ident(self.current_table)} WHERE {where_sql}"
        try:
            self.conn.execute(sql, where_params)
            self.conn.commit()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{exc}")
            return
        self.reload_table_data()


def main() -> None:
    app = QApplication(sys.argv)
    window = DbViewerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
