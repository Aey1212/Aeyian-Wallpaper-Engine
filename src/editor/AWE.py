#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
)
from PySide6.QtCore import Qt


_HOME = Path.home()
_WHICH = shutil.which

PROJECTS_DIR = _HOME / ".local" / "share" / "interactive-wallpapers"
CONFIG_PATH = _HOME / ".config" / "AWE.json" #TODO: actually use it.

AEYIAN_BLUE = "#3A41E1"
BTN_BG = "#2a2a2a"
BTN_TEXT = "#e1e1e1"
BTN_BORDER = "#3a3a3a"
BTN_HOVER = "#353535"

DARK_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: #1e1e1e;
        color: #e1e1e1;
    }}
    QLabel {{
        color: #e1e1e1;
    }}
    QPushButton {{
        background-color: {BTN_BG};
        color: {BTN_TEXT};
        border: 1px solid {BTN_BORDER};
        border-radius: 4px;
        padding: 6px 16px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {BTN_HOVER};
    }}
"""


def find_qdbus():
    # Plasma 6: qdbus6 (qt6-tools)
    # Plasma 5: qdbus or qdbus-qt5 (qt5-tools)
    for cmd in ("qdbus6", "qdbus", "qdbus-qt5"):
        if _WHICH(cmd):
            return cmd
    raise FileNotFoundError("No qdbus found. Install 'qt6-tools' or 'qt5-tools'.") # I hate backwards comp.


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AWE - Aeyian Wallpaper Engine")
        self.resize(1200, 800)

        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

        # 0 is main screen & 1 is editor
        self._views = QStackedWidget()
        self.setCentralWidget(self._views)
        self._main_screen = self._build_main_screen()
        self._editor_view = self._build_editor_view()
        self._views.addWidget(self._main_screen)
        self._views.addWidget(self._editor_view)
        self.show_main_screen()

    def show_main_screen(self):
        self._views.setCurrentIndex(0)

    def show_editor(self):
        self._views.setCurrentIndex(1)

    def _build_main_screen(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"background-color: #060916;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar_label = QLabel("Properties")
        sidebar_label.setStyleSheet(f"font-size: 16px; color: {AEYIAN_BLUE}; background: transparent;")
        sidebar_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        sidebar_layout.addWidget(sidebar_label)
        sidebar_layout.addStretch()
        sidebar_btn_row = QHBoxLayout()
        sidebar_btn_row.setSpacing(6)
        for name in ("Edit", "Rename", "Delete"):
            btn = QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: 1px solid {BTN_BORDER}; }}
                QPushButton:hover {{ background-color: {BTN_HOVER}; }}
            """)
            sidebar_btn_row.addWidget(btn)
        sidebar_layout.addLayout(sidebar_btn_row)

        # The thin line thingy inbetween
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #161954;")

        # Wallpaper area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)

        content_label = QLabel("Wallpapers")
        content_label.setStyleSheet(f"font-size: 24px; color: {AEYIAN_BLUE};")
        content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(content_label, 1)
        content_btn_row = QHBoxLayout()
        content_btn_row.setSpacing(6)
        content_btn_row.addWidget(QPushButton("+ New Project"))
        content_btn_row.addWidget(QPushButton("Settings"))
        content_btn_row.addStretch()
        content_layout.addLayout(content_btn_row)

        layout.addWidget(sidebar)
        layout.addWidget(separator)
        layout.addWidget(content, 1)

        return page

    def _build_editor_view(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("Editor")
        label.setStyleSheet(f"font-size: 24px; color: {AEYIAN_BLUE};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
