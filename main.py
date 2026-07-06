import sys

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.resize(320, 120)

        self.label = QLabel("Привет, мир!")
        self.button = QPushButton("Нажми меня")
        self.button.clicked.connect(self.on_button_click)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def on_button_click(self) -> None:
        self.label.setText("Кнопка нажата!")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
