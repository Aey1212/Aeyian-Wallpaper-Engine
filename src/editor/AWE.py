#!/usr/bin/env python3
import json
import random
import shutil
import string
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
    QScrollArea, QGridLayout, QDialog, QLineEdit, QSpinBox,
    QDialogButtonBox, QSizePolicy, QMessageBox, QInputDialog,
    QComboBox, QFormLayout,
)
from PySide6.QtGui import QPixmap, QImage, QColor, QDesktopServices
from PySide6.QtCore import Qt, QUrl


_HOME = Path.home()
_WHICH = shutil.which

PROJECTS_DIR = _HOME / ".local" / "share" / "interactive-wallpapers"
CONFIG_PATH = _HOME / ".config" / "AWE.json" #TODO: actually use it.

AWE_VERSION = "0.0.2" #TODO: actually pull from the fucking project.
AEYIAN_BLUE = "#3A41E1"
PLACEHOLDER_RED = "#e13b3e" # Let's hope people aren't stupid enough to not add pictures to their stuff

BTN_BG = "#2a2a2a"
BTN_TEXT = "#e1e1e1"
BTN_BORDER = "#3a3a3a"
BTN_HOVER = "#353535"

CARD_W = 160
CARD_H = 90
SIDEBAR_PREVIEW_W = 256
SIDEBAR_PREVIEW_H = 144

#TODO: Pull the theme from config and also possibly push via custom theme saving way way later?
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


def generate_project_id() -> str:
    # ID is better than name eh?
    timestamp = datetime.now().strftime("%d%m%y%H%M%S")
    suffix = ''.join(random.choice(string.ascii_uppercase) for _ in range(3))
    return f"{timestamp}-{suffix}"


def generate_red_preview(path: Path):
    img = QImage(CARD_W, CARD_H, QImage.Format.Format_RGB32)
    img.fill(QColor(PLACEHOLDER_RED))
    img.save(str(path))


class NewProjectDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setFixedSize(320, 180)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Project Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Wallpaper")
        layout.addWidget(self.name_input)

        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Width:"))
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 999999)
        self.width_input.setValue(1920)
        res_layout.addWidget(self.width_input)

        res_layout.addWidget(QLabel("Height:"))
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 999999)
        self.height_input.setValue(1080)
        res_layout.addWidget(self.height_input)
        layout.addLayout(res_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        return {
            "name": self.name_input.text().strip() or "Untitled",
            "width": self.width_input.value(),
            "height": self.height_input.value(),
        }


class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(360, 240)
        layout = QVBoxLayout(self)


        form = QFormLayout()
        form.setSpacing(10)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English"])
        form.addRow("Language:", self.language_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Aeyian Dark"])
        form.addRow("Theme:", self.theme_combo)

        layout.addLayout(form)
        layout.addSpacing(8)

        open_folder_btn = QPushButton("Open Projects Folder")
        open_folder_btn.clicked.connect(self._open_projects_folder)
        layout.addWidget(open_folder_btn)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Apply")
        btn_cancel = QPushButton("Cancel")
        btn_reset = QPushButton("Reset to Default")
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_reset)

        layout.addLayout(btn_row)

    def _open_projects_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(PROJECTS_DIR)))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AWE - Aeyian Wallpaper Engine")
        self.resize(1200, 800)

        self._selected_project = None

        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

        self._main_screen = self._build_main_screen()
        self.setCentralWidget(self._main_screen)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_grid()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_grid()


    def _scan_projects(self) -> list[dict]:
        projects = []
        if not PROJECTS_DIR.exists():
            return projects
        for d in sorted(PROJECTS_DIR.iterdir()):
            manifest = d / "project.json"
            if d.is_dir() and manifest.exists():
                try:
                    data = json.loads(manifest.read_text())
                    projects.append({
                        "name": data.get("name", d.name),
                        "id": data.get("id", d.name),
                        "path": d,
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        return projects


    def _on_new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        project_id = generate_project_id()
        project_dir = PROJECTS_DIR / project_id

        # Extremely unlikely but handle ID collision
        while project_dir.exists():
            project_id = generate_project_id()
            project_dir = PROJECTS_DIR / project_id

        project_dir.mkdir(parents=True)
        (project_dir / "assets").mkdir()

        generate_red_preview(project_dir / "preview.png")

        manifest = {
            "id": project_id,
            "name": values["name"],
            "format_version": "1.0.0",
            "editor_version": AWE_VERSION,
            "resolution": {
                "width": values["width"],
                "height": values["height"],
            },
            "layers": [],
            "properties": {},
        }
        (project_dir / "project.json").write_text(
            json.dumps(manifest, indent=2)
        )

        self._refresh_grid()
        self._select_project(project_dir)


    def _on_edit_project(self):
        if not self._selected_project:
            return
        awc_path = Path(__file__).parent / "AWC.py"
        subprocess.Popen([sys.executable, str(awc_path), str(self._selected_project)])
        QApplication.quit()

    def _on_rename_project(self):
        if not self._selected_project:
            return

        manifest_path = self._selected_project / "project.json"
        try:
            data = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            return

        current_name = data.get("name", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Project", "New name:", QLineEdit.EchoMode.Normal, current_name
        )
        if not ok or not new_name.strip():
            return

        data["name"] = new_name.strip()
        manifest_path.write_text(json.dumps(data, indent=2))

        self._refresh_grid()
        self._select_project(self._selected_project)


    def _on_delete_project(self):
        if not self._selected_project:
            return

        try:
            data = json.loads((self._selected_project / "project.json").read_text())
            name = data.get("name", self._selected_project.name)
        except (json.JSONDecodeError, OSError):
            name = self._selected_project.name

        reply = QMessageBox.question(
            self, "Delete Project",
            f"Delete '{name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        shutil.rmtree(self._selected_project)
        self._selected_project = None
        self._clear_sidebar()
        self._refresh_grid()


    def _on_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _refresh_grid(self):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projects = self._scan_projects()

        if not projects:
            hint = QLabel("No wallpapers yet")
            hint.setStyleSheet(f"font-size: 16px; color: #555; background: transparent;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(hint, 0, 0)
            return

        cols = max(1, (self._grid_container.width() - 24) // (CARD_W + 12))
        for i, project in enumerate(projects):
            card = self._make_card(project)
            self._grid_layout.addWidget(card, i // cols, i % cols)

    def _make_card(self, project: dict) -> QFrame:
        card = QFrame()
        card.setFixedSize(CARD_W, CARD_H + 24)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #252525;
                border: 2px solid transparent;
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(2)

        # Red or alive Xtreme — always loads preview.png (generated at creation)
        preview = QLabel()
        preview.setFixedSize(CARD_W, CARD_H)
        preview_path = project["path"] / "preview.png"
        pixmap = QPixmap(str(preview_path))
        preview.setPixmap(
            pixmap.scaled(CARD_W, CARD_H, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                          Qt.TransformationMode.SmoothTransformation)
        )
        layout.addWidget(preview)

        name = QLabel(project["name"])
        name.setStyleSheet("font-size: 11px; color: #e1e1e1; background: transparent; padding-left: 4px;")
        name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(name)

        card.project_path = project["path"]
        card.mousePressEvent = lambda e, p=project["path"]: self._select_project(p)

        return card


    def _select_project(self, path: Path):
        self._selected_project = path

        try:
            data = json.loads((path / "project.json").read_text())
            self._sidebar_label.setText(data.get("name", path.name))
            self._sidebar_id_label.setText(f"ID: {data.get('id', path.name)}")
            self._sidebar_format_ver.setText(f"Format Version: {data.get('format_version', '?')}")
            self._sidebar_editor_ver.setText(f"Editor Version: {data.get('editor_version', '?')}")
            res = data.get("resolution", {})
            self._sidebar_resolution.setText(f"Resolution: {res.get('width', '?')} x {res.get('height', '?')}")
        except (json.JSONDecodeError, OSError):
            self._sidebar_label.setText(path.name)
            self._sidebar_id_label.setText(f"ID: {path.name}")
            self._sidebar_format_ver.setText("")
            self._sidebar_editor_ver.setText("")
            self._sidebar_resolution.setText("")

        preview_path = path / "preview.png"
        pixmap = QPixmap(str(preview_path))
        self._sidebar_preview.setPixmap(
            pixmap.scaled(SIDEBAR_PREVIEW_W, SIDEBAR_PREVIEW_H,
                          Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                          Qt.TransformationMode.SmoothTransformation)
        )


        for i in range(self._grid_layout.count()):
            item = self._grid_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, QFrame) and hasattr(w, 'project_path'):
                    if w.project_path == path:
                        w.setStyleSheet(f"""
                            QFrame {{
                                background-color: #252525;
                                border: 2px solid {AEYIAN_BLUE};
                                border-radius: 4px;
                            }}
                        """)
                    else:
                        w.setStyleSheet(f"""
                            QFrame {{
                                background-color: #252525;
                                border: 2px solid transparent;
                                border-radius: 4px;
                            }}
                        """)


    def _clear_sidebar(self):
        self._sidebar_label.setText("Properties")
        self._sidebar_id_label.setText("")
        self._sidebar_format_ver.setText("")
        self._sidebar_editor_ver.setText("")
        self._sidebar_resolution.setText("")
        self._sidebar_preview.clear()
        self._sidebar_preview.setStyleSheet(f"background-color: {PLACEHOLDER_RED}; border-radius: 4px;")


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

        # Sidebar preview image
        self._sidebar_preview = QLabel()
        self._sidebar_preview.setFixedSize(SIDEBAR_PREVIEW_W, SIDEBAR_PREVIEW_H)
        self._sidebar_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sidebar_preview.setStyleSheet(f"background-color: {PLACEHOLDER_RED}; border-radius: 4px;")
        sidebar_layout.addWidget(self._sidebar_preview)

        # Project name
        self._sidebar_label = QLabel("Properties")
        self._sidebar_label.setStyleSheet(f"font-size: 16px; color: {AEYIAN_BLUE}; background: transparent;")
        self._sidebar_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        sidebar_layout.addWidget(self._sidebar_label)

        # Project ID
        self._sidebar_id_label = QLabel("")
        self._sidebar_id_label.setStyleSheet(f"font-size: 12px; color: #888; background: transparent;")
        self._sidebar_id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        sidebar_layout.addWidget(self._sidebar_id_label)

        # Project info labels
        info_style = f"font-size: 12px; color: #888; background: transparent;"
        self._sidebar_format_ver = QLabel("")
        self._sidebar_format_ver.setStyleSheet(info_style)
        sidebar_layout.addWidget(self._sidebar_format_ver)

        self._sidebar_editor_ver = QLabel("")
        self._sidebar_editor_ver.setStyleSheet(info_style)
        sidebar_layout.addWidget(self._sidebar_editor_ver)

        self._sidebar_resolution = QLabel("")
        self._sidebar_resolution.setStyleSheet(info_style)
        sidebar_layout.addWidget(self._sidebar_resolution)

        sidebar_layout.addStretch()

        # Sidebar buttons
        sidebar_btn_row = QHBoxLayout()
        sidebar_btn_row.setSpacing(6)

        self._btn_edit = QPushButton("Edit")
        self._btn_rename = QPushButton("Rename")
        self._btn_delete = QPushButton("Delete")

        for btn in (self._btn_edit, self._btn_rename, self._btn_delete):
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: 1px solid {BTN_BORDER}; }}
                QPushButton:hover {{ background-color: {BTN_HOVER}; }}
            """)
            sidebar_btn_row.addWidget(btn)

        self._btn_edit.clicked.connect(self._on_edit_project)
        self._btn_rename.clicked.connect(self._on_rename_project)
        self._btn_delete.clicked.connect(self._on_delete_project)

        sidebar_layout.addLayout(sidebar_btn_row)

        # The thin line thingy inbetween
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #161954;")

        # Wallpaper area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._grid_layout.setSpacing(12)
        scroll.setWidget(self._grid_container)

        content_layout.addWidget(scroll, 1)

        # Bottom buttons
        content_btn_row = QHBoxLayout()
        content_btn_row.setSpacing(6)
        new_btn = QPushButton("+ New Project")
        new_btn.clicked.connect(self._on_new_project)
        content_btn_row.addWidget(new_btn)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._on_settings)
        content_btn_row.addWidget(settings_btn)
        content_btn_row.addStretch()
        content_layout.addLayout(content_btn_row)

        layout.addWidget(sidebar)
        layout.addWidget(separator)
        layout.addWidget(content, 1)
        self._refresh_grid()

        return page


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
