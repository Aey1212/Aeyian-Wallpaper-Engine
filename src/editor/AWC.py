#!/usr/bin/env python3
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSplitter,
    QPushButton, QMenu, QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit,
    QColorDialog, QFileDialog, QScrollArea, QFormLayout,
)
from PySide6.QtGui import QPainter, QColor, QPixmap, QPolygonF, QImage
from PySide6.QtCore import Qt, QPointF, QRectF

from layers import (
    AddLayerDialog, AddEffectDialog, create_layer, create_effect,
    resolve_hierarchy, resolve_effect_hierarchy, toggle_layer_visibility,
    get_schema_for_layer, get_schema_for_effect, get_nested, set_nested,
)

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
    QTreeWidget {{
        background-color: #161616;
        color: #e1e1e1;
        border: none;
        outline: none;
    }}
    QTreeWidget::item {{
        padding: 4px;
    }}
    QTreeWidget::item:selected {{
        background-color: {BTN_HOVER};
    }}
    QTreeWidget::branch {{
        background-color: #161616;
    }}
    QCheckBox {{
        color: #e1e1e1;
        spacing: 6px;
        background: transparent;
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

    def __init__(self, project_path: Path, canvas_w: int, canvas_h: int, layers: list):
        super().__init__()
        self._project_path = project_path
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._layers = layers
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._hex_cache = None
        self._hex_cache_size = None
        self._image_cache = {}

        canvas_path = project_path / "canvas.png"
        if canvas_path.exists():
            self._canvas_pixmap = QPixmap(str(canvas_path))
        else:
            self._canvas_pixmap = None

    def invalidate_image_cache(self, rel_path: str = None):
        if rel_path is None:
            self._image_cache.clear()
        else:
            full_path = str(self._project_path / rel_path)
            self._image_cache.pop(full_path, None)

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

        render_layers = sorted(self._layers, key=lambda layer: layer.get("hierarchy", 0))
        for layer in render_layers:
            if layer.get("id", 0) == 0:
                continue
            if not layer.get("visible", True):
                continue
            layer_type = layer.get("type", "")
            pos = layer.get("position", {"x": 0, "y": 0})
            size = layer.get("size", {"width": self._canvas_w, "height": self._canvas_h})
            lx = self._offset_x + pos["x"] * self._scale
            ly = self._offset_y + pos["y"] * self._scale
            lw = size["width"] * self._scale
            lh = size["height"] * self._scale

            if layer_type == "solid_color":
                painter.fillRect(QRectF(lx, ly, lw, lh), QColor(layer.get("color", "#ffffff")))
            elif layer_type == "image":
                img_path = layer.get("image", "")
                if img_path:
                    full_path = str(self._project_path / img_path)
                    if full_path not in self._image_cache:
                        pm = QPixmap(full_path)
                        if not pm.isNull():
                            self._image_cache[full_path] = pm
                    cached = self._image_cache.get(full_path)
                    if cached:
                        painter.drawPixmap(QRectF(lx, ly, lw, lh).toAlignedRect(), cached)

        painter.end()

    def render_to_image(self) -> QImage:
        img = QImage(self._canvas_w, self._canvas_h, QImage.Format.Format_ARGB32)
        img.fill(QColor("#ffffff"))
        painter = QPainter(img)

        render_layers = sorted(self._layers, key=lambda layer: layer.get("hierarchy", 0))
        for layer in render_layers:
            if layer.get("id", 0) == 0:
                continue
            if not layer.get("visible", True):
                continue
            layer_type = layer.get("type", "")
            pos = layer.get("position", {"x": 0, "y": 0})
            size = layer.get("size", {"width": self._canvas_w, "height": self._canvas_h})
            lx, ly = pos["x"], pos["y"]
            lw, lh = size["width"], size["height"]

            if layer_type == "solid_color":
                painter.fillRect(QRectF(lx, ly, lw, lh), QColor(layer.get("color", "#ffffff")))
            elif layer_type == "image":
                img_path = layer.get("image", "")
                if img_path:
                    full_path = str(self._project_path / img_path)
                    cached = self._image_cache.get(full_path)
                    if not cached:
                        pm = QPixmap(full_path)
                        if not pm.isNull():
                            cached = pm
                    if cached:
                        painter.drawPixmap(QRectF(lx, ly, lw, lh).toAlignedRect(), cached)

        painter.end()
        return img


class CreatorWindow(QMainWindow):

    def __init__(self, project_path: Path):
        super().__init__()
        self._project_path = project_path

        try:
            data = json.loads((project_path / "project.json").read_text())
            self._project_name = data.get("name", project_path.name)
            res = data.get("resolution", {})
            self._canvas_w = res.get("width", 1920)
            self._canvas_h = res.get("height", 1080)
        except (json.JSONDecodeError, OSError):
            self._project_name = project_path.name
            self._canvas_w = 1920
            self._canvas_h = 1080

        try:
            layers_data = json.loads((project_path / "layers.json").read_text())
            self._layers = layers_data.get("layers", [])
            if resolve_hierarchy(self._layers):
                layers_data["layers"] = self._layers
                (project_path / "layers.json").write_text(json.dumps(layers_data, indent=2))
        except (json.JSONDecodeError, OSError):
            self._layers = []

        try:
            effects_data = json.loads((project_path / "effects.json").read_text())
            self._effects = effects_data.get("effects", [])
        except (json.JSONDecodeError, OSError):
            self._effects = []

        self._selected_layer = None

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

        self._layers_panel = QFrame()
        self._layers_panel.setMinimumWidth(100)
        self._layers_panel.setStyleSheet(f"background-color: {PANEL_BG};")
        self._layers_layout = QVBoxLayout(self._layers_panel)
        self._layers_layout.setContentsMargins(8, 8, 8, 8)
        self._rebuild_layer_panel()
        splitter.addWidget(self._layers_panel)

        self._canvas_view = CanvasView(self._project_path, self._canvas_w, self._canvas_h, self._layers)
        self._canvas_view.setMinimumWidth(300)
        splitter.addWidget(self._canvas_view)

        self._inspector_panel = QFrame()
        self._inspector_panel.setMinimumWidth(150)
        self._inspector_panel.setStyleSheet(f"background-color: {PANEL_BG};")
        self._inspector_layout = QVBoxLayout(self._inspector_panel)
        self._inspector_layout.setContentsMargins(8, 8, 8, 8)
        self._rebuild_inspector()
        splitter.addWidget(self._inspector_panel)

        splitter.setSizes([200, 920, 280])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)
        root.addWidget(splitter, 1)

    def _on_add_layer(self):
        dialog = AddLayerDialog(self)
        if not dialog.exec():
            return

        selected_layer_type = dialog.get_selected_layer_type()
        if not selected_layer_type:
            return

        self._layers.append(create_layer(self._layers, selected_layer_type, self._canvas_w, self._canvas_h))
        resolve_hierarchy(self._layers)
        self._save_layers()
        self._rebuild_layer_panel()
        self._canvas_view.update()

    def _on_visibility_toggled(self, layer_id: int, visible: bool):
        toggle_layer_visibility(self._project_path, self._layers, layer_id, visible)
        self._canvas_view.update()

    def _save_layers(self):
        layers_path = self._project_path / "layers.json"
        data = json.loads(layers_path.read_text())
        data["layers"] = self._layers
        layers_path.write_text(json.dumps(data, indent=2))

    def _rebuild_layer_panel(self):
        while self._layers_layout.count():
            item = self._layers_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        layers_header = QLabel("Layers")
        layers_header.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        self._layers_layout.addWidget(layers_header)

        ordered_layers = sorted(
            (layer for layer in self._layers if layer.get("id", 0) != 0),
            key=lambda layer: layer.get("hierarchy", 0),
            reverse=True,
        )

        for layer in ordered_layers:
            layer_id = layer["id"]
            is_selected = self._selected_layer is not None and self._selected_layer.get("id") == layer_id
            row_bg = "#2a2a3a" if is_selected else "transparent"

            row_widget = QWidget()
            row_widget.setStyleSheet(f"background: {row_bg};")
            row_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            row_widget.mousePressEvent = lambda e, lid=layer_id: self._on_layer_selected(lid)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(4)
            cb = QCheckBox()
            cb.setChecked(layer.get("visible", True))
            cb.toggled.connect(lambda checked, lid=layer_id: self._on_visibility_toggled(lid, checked))
            row_layout.addWidget(cb)
            name_label = QLabel(layer.get("name", f"Layer {layer_id}"))
            name_label.setStyleSheet("font-size: 12px; color: #e1e1e1; background: transparent;")
            row_layout.addWidget(name_label)
            row_layout.addStretch()
            self._layers_layout.addWidget(row_widget)

        self._layers_layout.addStretch()
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
        add_layer_btn.clicked.connect(self._on_add_layer)
        self._layers_layout.addWidget(add_layer_btn)

    def _on_layer_selected(self, layer_id: int):
        self._selected_layer = None
        for layer in self._layers:
            if layer.get("id") == layer_id:
                self._selected_layer = layer
                break
        self._rebuild_layer_panel()
        self._rebuild_inspector()

    def _rebuild_inspector(self):
        while self._inspector_layout.count():
            item = self._inspector_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        inspector_header = QLabel("Inspector")
        inspector_header.setStyleSheet(f"font-size: 14px; color: {AEYIAN_BLUE}; background: transparent;")
        self._inspector_layout.addWidget(inspector_header)

        if self._selected_layer is None:
            self._inspector_layout.addStretch()
            return

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        # Layer properties
        schema = get_schema_for_layer(self._selected_layer)
        form = QFormLayout()
        form.setSpacing(6)
        for entry in schema:
            label = QLabel(entry["label"])
            label.setStyleSheet("font-size: 12px; color: #aaa; background: transparent;")
            widget = self._make_property_widget(entry, self._selected_layer, self._on_property_changed)
            if widget is not None:
                form.addRow(label, widget)
        form_wrapper = QWidget()
        form_wrapper.setStyleSheet("background: transparent;")
        form_wrapper.setLayout(form)
        content_layout.addWidget(form_wrapper)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3a3a3a;")
        content_layout.addWidget(sep)

        # Effects header + add button
        effects_header_row = QWidget()
        effects_header_row.setStyleSheet("background: transparent;")
        effects_header_layout = QHBoxLayout(effects_header_row)
        effects_header_layout.setContentsMargins(0, 0, 0, 0)
        effects_label = QLabel("Effects")
        effects_label.setStyleSheet(f"font-size: 13px; color: {AEYIAN_BLUE}; background: transparent;")
        effects_header_layout.addWidget(effects_label)
        effects_header_layout.addStretch()
        add_effect_btn = QPushButton("+")
        add_effect_btn.setFixedSize(24, 24)
        add_effect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_effect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BTN_BG}; color: #e1e1e1;
                border: 1px solid {BTN_BORDER}; border-radius: 4px;
                font-size: 14px; font-weight: bold; padding: 0px;
            }}
            QPushButton:hover {{ background-color: {BTN_HOVER}; }}
        """)
        add_effect_btn.clicked.connect(self._on_add_effect)
        effects_header_layout.addWidget(add_effect_btn)
        content_layout.addWidget(effects_header_row)

        # Effects for this layer
        layer_id = self._selected_layer.get("id")
        layer_effects = sorted(
            (e for e in self._effects if e.get("layer_id") == layer_id),
            key=lambda e: e.get("hierarchy", 0),
        )

        for effect in layer_effects:
            effect_frame = QFrame()
            effect_frame.setStyleSheet(f"background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 4px;")
            effect_layout = QVBoxLayout(effect_frame)
            effect_layout.setContentsMargins(6, 4, 6, 4)
            effect_layout.setSpacing(4)

            effect_name = QLabel(f"{effect.get('hierarchy', '?')}. {effect.get('name', 'Effect')}")
            effect_name.setStyleSheet(f"font-size: 12px; color: #e1e1e1; background: transparent; border: none;")
            effect_layout.addWidget(effect_name)

            effect_schema = get_schema_for_effect(effect)
            effect_form = QFormLayout()
            effect_form.setSpacing(4)
            effect_cb = lambda k, v, eff=effect: self._on_effect_property_changed(eff, k, v)
            for entry in effect_schema:
                label = QLabel(entry["label"])
                label.setStyleSheet("font-size: 11px; color: #888; background: transparent; border: none;")
                widget = self._make_property_widget(entry, effect, effect_cb)
                if widget is not None:
                    effect_form.addRow(label, widget)
            effect_form_wrapper = QWidget()
            effect_form_wrapper.setStyleSheet("background: transparent; border: none;")
            effect_form_wrapper.setLayout(effect_form)
            effect_layout.addWidget(effect_form_wrapper)

            content_layout.addWidget(effect_frame)

        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._inspector_layout.addWidget(scroll, 1)

    def _make_property_widget(self, entry: dict, data_source: dict, callback) -> QWidget | None:
        key = entry["key"]
        widget_type = entry["widget"]
        current_value = get_nested(data_source, key)

        if widget_type == "text":
            widget = QLineEdit(str(current_value or ""))
            widget.setStyleSheet("background: #2a2a2a; color: #e1e1e1; border: 1px solid #3a3a3a; padding: 3px;")
            widget.editingFinished.connect(lambda k=key, w=widget, cb=callback: cb(k, w.text()))
            return widget

        if widget_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            widget.toggled.connect(lambda checked, k=key, cb=callback: cb(k, checked))
            return widget

        if widget_type == "int":
            widget = QSpinBox()
            widget.setRange(entry.get("min", -999999), entry.get("max", 999999))
            widget.setValue(int(current_value or 0))
            widget.setStyleSheet("background: #2a2a2a; color: #e1e1e1; border: 1px solid #3a3a3a; padding: 3px;")
            widget.valueChanged.connect(lambda val, k=key, cb=callback: cb(k, val))
            return widget

        if widget_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(entry.get("min", 0.0), entry.get("max", 1.0))
            widget.setSingleStep(0.05)
            widget.setDecimals(2)
            widget.setValue(float(current_value or 0.0))
            widget.setStyleSheet("background: #2a2a2a; color: #e1e1e1; border: 1px solid #3a3a3a; padding: 3px;")
            widget.valueChanged.connect(lambda val, k=key, cb=callback: cb(k, val))
            return widget

        if widget_type == "color":
            color_str = str(current_value or "#ffffff")
            widget = QPushButton()
            widget.setFixedHeight(24)
            widget.setStyleSheet(f"background-color: {color_str}; border: 1px solid #3a3a3a;")
            widget.clicked.connect(lambda _, k=key, w=widget, c=color_str, cb=callback: self._on_color_pick(k, w, c, cb))
            return widget

        if widget_type == "file":
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            line = QLineEdit(str(current_value or ""))
            line.setStyleSheet("background: #2a2a2a; color: #e1e1e1; border: 1px solid #3a3a3a; padding: 3px;")
            line.editingFinished.connect(lambda k=key, w=line, cb=callback: cb(k, w.text()))
            row_layout.addWidget(line)
            browse = QPushButton("...")
            browse.setFixedWidth(28)
            browse.clicked.connect(lambda _, k=key, w=line: self._on_file_browse(k, w))
            row_layout.addWidget(browse)
            return row

        return None

    def _on_property_changed(self, key: str, value):
        if self._selected_layer is None:
            return
        set_nested(self._selected_layer, key, value)
        self._save_layers()
        if key == "name" or key == "visible":
            self._rebuild_layer_panel()
        self._canvas_view.update()

    def _on_color_pick(self, key: str, button: QPushButton, current: str, callback=None):
        color = QColorDialog.getColor(QColor(current), self, "Pick Color")
        if not color.isValid():
            return
        hex_color = color.name()
        button.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #3a3a3a;")
        cb = callback or self._on_property_changed
        cb(key, hex_color)

    def _on_file_browse(self, key: str, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", str(Path.home()))
        if not path:
            return
        src = Path(path)
        layer_id = self._selected_layer.get("id")
        dest_name = f"{layer_id}{src.suffix}"
        dest = self._project_path / "assets" / dest_name
        shutil.copy2(str(src), str(dest))
        rel = f"assets/{dest_name}"
        line_edit.setText(rel)
        self._canvas_view.invalidate_image_cache(rel)
        self._on_property_changed(key, rel)

    def _on_add_effect(self):
        if self._selected_layer is None:
            return
        dialog = AddEffectDialog(self)
        if not dialog.exec():
            return
        selected_effect_type = dialog.get_selected_effect_type()
        if not selected_effect_type:
            return
        layer_id = self._selected_layer.get("id")
        new_effect = create_effect(self._effects, layer_id, selected_effect_type)
        self._effects.append(new_effect)
        resolve_effect_hierarchy(self._effects, layer_id)
        self._save_effects()
        self._rebuild_inspector()

    def _on_effect_property_changed(self, effect: dict, key: str, value):
        set_nested(effect, key, value)
        self._save_effects()

    def _save_effects(self):
        effects_path = self._project_path / "effects.json"
        effects_path.write_text(json.dumps({"effects": self._effects}, indent=2))

    def closeEvent(self, event):
        preview = self._canvas_view.render_to_image()
        preview = preview.scaled(160, 90, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        preview.save(str(self._project_path / "preview.png"))
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
