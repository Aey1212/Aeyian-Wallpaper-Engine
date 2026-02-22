#!/usr/bin/env python3
import json
import math
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSplitter,
    QPushButton, QMenu,
)
from PySide6.QtGui import QPainter, QColor, QPixmap, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF

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
    QMenu {{
        background-color: #252525;
        color: #e1e1e1;
        border: 1px solid {BTN_BORDER};
        padding: 4px 0px;
    }}
    QMenu::item {{
        padding: 6px 24px;
    }}
    QMenu::item:selected {{
        background-color: {BTN_HOVER};
    }}
"""

PANEL_BG = "#161616"
PANEL_BORDER = "#2a2a2a"
AEYIAN_BLUE = "#3A41E1"


HEX_LIGHT = "#3a3a3a"
HEX_MID = "#2e2e2e"
HEX_DARK = "#232323"
HEX_RADIUS = 12


class CanvasView(QWidget):

    def __init__(self, project_path: Path, layers: list):
        super().__init__()
        self._layers = layers
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0

        canvas_path = project_path / "canvas.png"
        if canvas_path.exists():
            self._canvas_pixmap = QPixmap(str(canvas_path))
            self._canvas_w = self._canvas_pixmap.width()
            self._canvas_h = self._canvas_pixmap.height()
        else:
            try:
                data = json.loads((project_path / "project.json").read_text())
                res = data.get("resolution", {})
                self._canvas_w = res.get("width", 1920)
                self._canvas_h = res.get("height", 1080)
            except (json.JSONDecodeError, OSError):
                self._canvas_w = 1920
                self._canvas_h = 1080
            self._canvas_pixmap = None

        self._hex_cache = None
        self._hex_cache_size = None

    def _update_transform(self):
        padding = 20
        avail_w = self.width() - padding * 2
        avail_h = self.height() - padding * 2
        if avail_w <= 0 or avail_h <= 0:
            return
        scale_x = avail_w / self._canvas_w
        scale_y = avail_h / self._canvas_h
        self._scale = min(scale_x, scale_y)
        scaled_w = self._canvas_w * self._scale
        scaled_h = self._canvas_h * self._scale
        self._offset_x = (self.width() - scaled_w) / 2
        self._offset_y = (self.height() - scaled_h) / 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_transform()
        self.update()

    def _build_hex_cache(self, w, h):
        r = HEX_RADIUS
        hex_w = math.sqrt(3) * r
        hex_h = 2 * r
        row_step = hex_h * 0.75
        colors = [QColor(HEX_LIGHT), QColor(HEX_MID), QColor(HEX_DARK)]

        pixmap = QPixmap(int(w), int(h))
        pixmap.fill(QColor(HEX_DARK))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        rows = int(h / row_step) + 3
        cols = int(w / hex_w) + 3

        for row in range(-1, rows):
            for col in range(-1, cols):
                cx = col * hex_w + (hex_w * 0.5 if row % 2 else 0)
                cy = row * row_step
                ci = ((row % 3) + col) % 3
                painter.setBrush(colors[ci])
                points = []
                for i in range(6):
                    angle_rad = math.radians(60 * i - 30)
                    points.append(QPointF(
                        cx + r * math.cos(angle_rad),
                        cy + r * math.sin(angle_rad),
                    ))
                painter.drawPolygon(QPolygonF(points))

        painter.end()
        self._hex_cache = pixmap
        self._hex_cache_size = (int(w), int(h))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        canvas_rect = QRectF(
            self._offset_x, self._offset_y,
            self._canvas_w * self._scale,
            self._canvas_h * self._scale,
        )

        cw = int(canvas_rect.width())
        ch = int(canvas_rect.height())
        if cw > 0 and ch > 0:
            if self._hex_cache is None or self._hex_cache_size != (cw, ch):
                self._build_hex_cache(cw, ch)
            painter.drawPixmap(canvas_rect.toAlignedRect(), self._hex_cache)

        if self._canvas_pixmap:
            painter.drawPixmap(canvas_rect.toAlignedRect(), self._canvas_pixmap)

        for layer in self._layers:
            if layer.get("id", 0) == 0:
                continue
            layer_type = layer.get("type", "")
            if layer_type == "solid_color":
                pos = layer.get("position", {"x": 0, "y": 0})
                size = layer.get("size", {"width": self._canvas_w, "height": self._canvas_h})
                lx = self._offset_x + pos["x"] * self._scale
                ly = self._offset_y + pos["y"] * self._scale
                lw = size["width"] * self._scale
                lh = size["height"] * self._scale
                painter.fillRect(QRectF(lx, ly, lw, lh), QColor(layer.get("color", "#ffffff")))

        painter.end()


class CreatorWindow(QMainWindow):

    def __init__(self, project_path: Path):
        super().__init__()
        self._project_path = project_path

        try:
            data = json.loads((project_path / "project.json").read_text())
            self._project_name = data.get("name", project_path.name)
            self._layers = data.get("layers", [])
        except (json.JSONDecodeError, OSError):
            self._project_name = project_path.name
            self._layers = []

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

        top_layout.addSpacing(16)

        menu_btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: #e1e1e1;
                padding: 4px 10px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {BTN_HOVER};
                border-radius: 4px;
            }}
            QPushButton::menu-indicator {{ image: none; }}
        """

        project_btn = QPushButton("Project")
        project_btn.setStyleSheet(menu_btn_style)
        project_menu = QMenu(project_btn)
        project_menu.addAction("Save")
        project_menu.addAction("Save As")
        project_menu.addSeparator()
        project_menu.addAction("Configure")
        project_btn.setMenu(project_menu)
        top_layout.addWidget(project_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(menu_btn_style)
        edit_menu = QMenu(edit_btn)
        edit_menu.addAction("Undo")
        edit_menu.addAction("Redo")
        edit_menu.addSeparator()
        edit_menu.addAction("Cut")
        edit_menu.addAction("Copy")
        edit_menu.addAction("Paste")
        edit_btn.setMenu(edit_menu)
        top_layout.addWidget(edit_btn)

        help_btn = QPushButton("Help")
        help_btn.setStyleSheet(menu_btn_style)
        help_menu = QMenu(help_btn)
        help_menu.addAction("Documentation")
        help_menu.addAction("About AWC")
        help_btn.setMenu(help_menu)
        top_layout.addWidget(help_btn)

        top_layout.addStretch()
        root.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #161954; width: 2px; }")

        layers_panel = QFrame()
        layers_panel.setMinimumWidth(100)
        layers_panel.setStyleSheet(f"background-color: {PANEL_BG};")
        layers_layout = QVBoxLayout(layers_panel)
        layers_layout.setContentsMargins(8, 8, 8, 8)
        layers_header = QLabel("Layers")
        layers_header.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        layers_layout.addWidget(layers_header)

        for layer in self._layers:
            if layer.get("id", 0) == 0:
                continue
            row = QLabel(layer.get("name", f"Layer {layer['id']}"))
            row.setStyleSheet("font-size: 12px; color: #e1e1e1; background: transparent; padding: 4px 0px;")
            layers_layout.addWidget(row)

        layers_layout.addStretch()
        add_layer_btn = QPushButton("+")
        add_layer_btn.setFixedSize(32, 32)
        add_layer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_layer_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BTN_BG};
                color: #e1e1e1;
                border: 1px solid {BTN_BORDER};
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {BTN_HOVER};
                border-color: #e1e1e1;
            }}
            QPushButton:pressed {{
                background-color: #444444;
            }}
        """)
        layers_layout.addWidget(add_layer_btn)
        splitter.addWidget(layers_panel)

        canvas = CanvasView(self._project_path, self._layers)
        canvas.setMinimumWidth(300)
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
