#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSplitter,
)
from PySide6.QtCore import Qt

#TODO: Pull the theme from config

AWE_PATH = Path(__file__).parent / "AWE.py"

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

PANEL_BG = "#161616"
PANEL_BORDER = "#2a2a2a"
AEYIAN_BLUE = "#3A41E1"


class CreatorWindow(QMainWindow):

    def __init__(self, project_path: Path):
        super().__init__()
        self._project_path = project_path

        try:
            data = json.loads((project_path / "project.json").read_text())
            self._project_name = data.get("name", project_path.name)
        except (json.JSONDecodeError, OSError):
            self._project_name = project_path.name

        self.setWindowTitle(f"AWC - {self._project_name}")
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet(f"background-color: {PANEL_BG}; border-bottom: 1px solid {PANEL_BORDER};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)

        name_label = QLabel(self._project_name)
        name_label.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        top_layout.addWidget(name_label)

        top_layout.addStretch()
        root.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #161954; width: 2px; }")

        layers_panel = QFrame()
        layers_panel.setMinimumWidth(100)
        layers_panel.setStyleSheet(f"background-color: {PANEL_BG};")
        layers_layout = QVBoxLayout(layers_panel)
        layers_layout.setContentsMargins(8, 8, 8, 8)
        layers_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layers_header = QLabel("Layers")
        layers_header.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        layers_layout.addWidget(layers_header)
        splitter.addWidget(layers_panel)

        canvas = QFrame()
        canvas.setMinimumWidth(300)
        canvas.setStyleSheet("background-color: #1e1e1e;")
        splitter.addWidget(canvas)

        inspector_panel = QFrame()
        inspector_panel.setMinimumWidth(150)
        inspector_panel.setStyleSheet(f"background-color: {PANEL_BG};")
        inspector_layout = QVBoxLayout(inspector_panel)
        inspector_layout.setContentsMargins(8, 8, 8, 8)
        inspector_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        inspector_header = QLabel("Inspector")
        inspector_header.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        inspector_layout.addWidget(inspector_header)
        splitter.addWidget(inspector_panel)

        splitter.setSizes([200, 920, 280])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)
        root.addWidget(splitter, 1)

    def closeEvent(self, event):
        subprocess.Popen([sys.executable, str(AWE_PATH)])
        event.accept()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: AWC.py <project_path>")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    if not (project_path / "project.json").exists():
        print(f"No project.json found in {project_path}")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = CreatorWindow(project_path)
    window.show()
    sys.exit(app.exec())
