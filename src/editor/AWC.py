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
    QColorDialog, QFileDialog, QScrollArea, QFormLayout, QComboBox, QDialog,
)
from PySide6.QtGui import QPainter, QColor, QPixmap, QPolygonF, QImage
from PySide6.QtCore import Qt, QPointF, QRect, QTimer, QUrl, Signal
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow, QSGRendererInterface
from PySide6.QtQuickWidgets import QQuickWidget

from layers import (
    AddLayerDialog, AddEffectDialog, create_layer, create_effect,
    resolve_hierarchy, resolve_effect_hierarchy, toggle_layer_visibility,
    swap_layer_order, delete_layer, delete_effect,
    get_schema_for_layer, get_schema_for_effect, get_nested, set_nested,
    Effects, PROJECT_SCHEMA,
)
from atomicio import atomic_write_json
from AWE import AWE_VERSION
from AWV import grab_frame

#TODO: Pull the theme from config

AWE_PATH = Path(__file__).parent / "AWE.py"
CANVAS_PATH = Path(__file__).parent / "canvas.qml"

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
    QTreeWidget::item:disabled {{
        color: #666666;
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


def build_hex_pixmap(w: int, h: int) -> QPixmap:
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
    return pixmap


class HexProvider(QQuickImageProvider):

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Pixmap)

    def requestPixmap(self, id: str, size, requested_size) -> QPixmap:
        w, h = (int(part) for part in id.split("x"))
        return build_hex_pixmap(w, h)


class CanvasView(QQuickWidget):

    preview_state_changed = Signal()

    def __init__(self, project_path: Path, canvas_w: int, canvas_h: int, layers: list, effects: list):
        super().__init__()
        self._project_path = project_path
        self._canvas_w = canvas_w
        self._canvas_h = canvas_h
        self._layers = layers
        self._effects = effects
        self._base_scale = 1.0
        self._user_zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._panning = False
        self._pan_start = None
        self._pan_origin = (0.0, 0.0)
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._hex_size = None
        self._frame_hue = 0.0
        self._playing = False
        self._preview_time = 0.0
        self._sim_cursor = QPointF(0.5, 0.5)
        self._track_cursor = False
        self._dirty = False
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)  # ~60fps
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.engine().addImageProvider("editor", HexProvider())
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setSource(QUrl.fromLocalFile(str(CANVAS_PATH)))
        self._root = self.rootObject()
        self._root.setProperty("canvasWidth", canvas_w)
        self._root.setProperty("canvasHeight", canvas_h)
        canvas_path = project_path / "canvas.png"
        if canvas_path.exists():
            self._root.setProperty("canvasSource", QUrl.fromLocalFile(str(canvas_path)))
        self._push_scene()

    def request_update(self):
        self._dirty = True

    def _scene_properties(self) -> dict:
        layers = sorted((dict(layer) for layer in self._layers), key=lambda layer: layer.get("hierarchy", 0))
        for layer in layers:
            image = self._project_path / layer.get("image", "")
            if layer.get("image") and image.exists():
                layer["image_stamp"] = int(image.stat().st_mtime * 1000)
        return {
            "projectPath": str(self._project_path),
            "layers": layers,
            "effects": self._effects,
        }

    def _push_scene(self):
        for key, value in self._scene_properties().items():
            self._root.setProperty(key, value)

    def _on_tick(self):
        if not self.isVisible():
            return
        self._frame_hue = (self._frame_hue + 0.005) % 1.0
        self._root.setProperty("frameHue", self._frame_hue)
        if self._playing:
            self._preview_time += 0.016
            self.preview_state_changed.emit()
        if self._dirty:
            self._dirty = False
            self._push_scene()

    def set_playing(self, val: bool):
        self._playing = val
        if not val:
            self._preview_time = 0.0
        self.preview_state_changed.emit()

    def set_track_cursor(self, val: bool):
        self._track_cursor = val

    def _update_transform(self):
        padding = 20
        avail_w = self.width() - padding * 2
        avail_h = self.height() - padding * 2
        if avail_w <= 0 or avail_h <= 0:
            return
        fit_x = avail_w / self._canvas_w
        fit_y = avail_h / self._canvas_h
        self._base_scale = min(fit_x, fit_y)
        self._scale = self._base_scale * self._user_zoom
        scaled_w = self._canvas_w * self._scale
        scaled_h = self._canvas_h * self._scale
        self._offset_x = (self.width() - scaled_w) / 2 + self._pan_x
        self._offset_y = (self.height() - scaled_h) / 2 + self._pan_y
        self._root.setProperty("viewScale", self._scale)
        self._root.setProperty("offsetX", math.floor(self._offset_x))
        self._root.setProperty("offsetY", math.floor(self._offset_y))
        hex_size = (max(1, int(self._canvas_w * self._base_scale)), max(1, int(self._canvas_h * self._base_scale)))
        if hex_size != self._hex_size:
            self._hex_size = hex_size
            self._root.setProperty("hexSource", QUrl(f"image://editor/{hex_size[0]}x{hex_size[1]}"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_transform()

    def wheelEvent(self, event):
        if self._scale <= 0:
            event.ignore()
            return
        notches = event.angleDelta().y() / 120.0
        if notches == 0:
            event.ignore()
            return
        zoom_factor = 1.15 ** notches
        new_zoom = max(0.1, min(10.0, self._user_zoom * zoom_factor))
        if new_zoom == self._user_zoom:
            event.accept()
            return

        cursor_pos = event.position()
        canvas_x = (cursor_pos.x() - self._offset_x) / self._scale
        canvas_y = (cursor_pos.y() - self._offset_y) / self._scale

        self._user_zoom = new_zoom
        new_scale = self._base_scale * new_zoom
        new_center_x = (self.width() - self._canvas_w * new_scale) / 2
        new_center_y = (self.height() - self._canvas_h * new_scale) / 2
        self._pan_x = cursor_pos.x() - new_center_x - canvas_x * new_scale
        self._pan_y = cursor_pos.y() - new_center_y - canvas_y * new_scale

        self._update_transform()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self._pan_origin = (self._pan_x, self._pan_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_x = self._pan_origin[0] + delta.x()
            self._pan_y = self._pan_origin[1] + delta.y()
            self._update_transform()
            event.accept()
            return
        if self._track_cursor and self._scale > 0:
            canvas_w_px = self._canvas_w * self._scale
            canvas_h_px = self._canvas_h * self._scale
            if canvas_w_px > 0 and canvas_h_px > 0:
                x = max(0.0, min(1.0, (event.position().x() - self._offset_x) / canvas_w_px))
                y = max(0.0, min(1.0, (event.position().y() - self._offset_y) / canvas_h_px))
                self._sim_cursor = QPointF(x, y)
                self._root.setProperty("cursorX", x)
                self._root.setProperty("cursorY", y)
                self.preview_state_changed.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self._pan_start = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            if event.key() == Qt.Key.Key_F:
                self._user_zoom = 1.0
                self._pan_x = 0.0
                self._pan_y = 0.0
                self._update_transform()
                event.accept()
                return
            if event.key() == Qt.Key.Key_C:
                if self._base_scale > 0:
                    self._user_zoom = 1.0 / self._base_scale
                self._pan_x = 0.0
                self._pan_y = 0.0
                self._update_transform()
                event.accept()
                return
        super().keyPressEvent(event)

    def render_to_image(self) -> QImage:
        project = {"width": self._canvas_w, "height": self._canvas_h, "scene": self._scene_properties()}
        return grab_frame(project, 0.5, 0.5)


class CreatorWindow(QMainWindow):

    NON_RENDER_KEYS = frozenset({"name"})

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
                atomic_write_json(project_path / "layers.json", layers_data)
        except (json.JSONDecodeError, OSError):
            self._layers = []

        try:
            effects_data = json.loads((project_path / "effects.json").read_text())
            self._effects = effects_data.get("effects", [])
        except (json.JSONDecodeError, OSError):
            self._effects = []

        self._selected_layer = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(250)
        self._save_timer.timeout.connect(self._flush_pending_saves)
        self._pending_save_layers = False
        self._pending_save_effects = False

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

        def _stub_actions(menu, labels):
            for label in labels:
                act = menu.addAction(label)
                act.setEnabled(False)

        project_btn = QPushButton("Project")
        project_btn.setStyleSheet(menu_btn_style)
        project_menu = QMenu(project_btn)
        _stub_actions(project_menu, ["Save", "Save As"])
        project_menu.addSeparator()
        configure_action = project_menu.addAction("Configure")
        configure_action.triggered.connect(self._on_configure_project)
        project_btn.setMenu(project_menu)
        top_layout.addWidget(project_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(menu_btn_style)
        edit_menu = QMenu(edit_btn)
        _stub_actions(edit_menu, ["Undo", "Redo"])
        edit_menu.addSeparator()
        _stub_actions(edit_menu, ["Cut", "Copy", "Paste"])
        edit_btn.setMenu(edit_menu)
        top_layout.addWidget(edit_btn)

        help_btn = QPushButton("Help")
        help_btn.setStyleSheet(menu_btn_style)
        help_menu = QMenu(help_btn)
        _stub_actions(help_menu, ["Documentation", "About AWC"])
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

        self._canvas_view = CanvasView(self._project_path, self._canvas_w, self._canvas_h, self._layers, self._effects)
        self._canvas_view.setMinimumWidth(300)

        canvas_container = QWidget()
        canvas_container.setStyleSheet("background: transparent;")
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        canvas_layout.addWidget(self._canvas_view, 1)
        canvas_layout.addWidget(self._build_status_strip())

        splitter.addWidget(canvas_container)
        self._canvas_view.preview_state_changed.connect(self._refresh_preview_status)

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
        self._canvas_view.request_update()

    def _on_visibility_toggled(self, layer_id: int, visible: bool):
        toggle_layer_visibility(self._project_path, self._layers, layer_id, visible)
        self._canvas_view.request_update()

    def _on_layer_move(self, layer_id: int, direction: str):
        if swap_layer_order(self._layers, layer_id, direction):
            self._save_layers()
            self._rebuild_layer_panel()
            self._canvas_view.request_update()

    def _on_layer_delete(self, layer_id: int):
        if self._selected_layer and self._selected_layer.get("id") == layer_id:
            self._selected_layer = None
        delete_layer(self._project_path, self._layers, self._effects, layer_id)
        self._save_layers()
        self._save_effects()
        self._rebuild_layer_panel()
        self._rebuild_inspector()
        self._canvas_view.request_update()

    def _save_layers(self):
        layers_path = self._project_path / "layers.json"
        data = json.loads(layers_path.read_text())
        data["layers"] = self._layers
        atomic_write_json(layers_path, data)
        self._pending_save_layers = False

    def _save_effects(self):
        effects_path = self._project_path / "effects.json"
        atomic_write_json(effects_path, {"effects": self._effects})
        self._pending_save_effects = False

    def _schedule_save_layers(self):
        self._pending_save_layers = True
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _schedule_save_effects(self):
        self._pending_save_effects = True
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _flush_pending_saves(self):
        if self._pending_save_layers:
            self._save_layers()
        if self._pending_save_effects:
            self._save_effects()

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

        layer_btn_style = f"""
            QPushButton {{
                background: transparent; border: none;
                color: #888; font-size: 12px; padding: 0px;
            }}
            QPushButton:hover {{ color: #e1e1e1; }}
            QPushButton:disabled {{ color: #333; }}
        """
        delete_btn_style = f"""
            QPushButton {{
                background: transparent; border: none;
                color: #888; font-size: 12px; padding: 0px;
            }}
            QPushButton:hover {{ color: #e13b3e; }}
        """

        for i, layer in enumerate(ordered_layers):
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

            up_btn = QPushButton("▲")
            up_btn.setFixedSize(20, 20)
            up_btn.setStyleSheet(layer_btn_style)
            up_btn.setEnabled(i > 0)
            up_btn.clicked.connect(lambda _, lid=layer_id: self._on_layer_move(lid, "up"))
            row_layout.addWidget(up_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet(delete_btn_style)
            del_btn.clicked.connect(lambda _, lid=layer_id: self._on_layer_delete(lid))
            row_layout.addWidget(del_btn)

            down_btn = QPushButton("▼")
            down_btn.setFixedSize(20, 20)
            down_btn.setStyleSheet(layer_btn_style)
            down_btn.setEnabled(i < len(ordered_layers) - 1)
            down_btn.clicked.connect(lambda _, lid=layer_id: self._on_layer_move(lid, "down"))
            row_layout.addWidget(down_btn)

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

        # Effects section
        layer_type = self._selected_layer.get("type", "")
        if Effects.has_effects(layer_type):
            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #3a3a3a;")
            content_layout.addWidget(sep)

            # Effects header and adder and possibly some other things
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

                effect_header = QWidget()
                effect_header.setStyleSheet("background: transparent; border: none;")
                effect_header_layout = QHBoxLayout(effect_header)
                effect_header_layout.setContentsMargins(0, 0, 0, 0)
                effect_header_layout.setSpacing(4)

                effect_name = QLabel(f"{effect.get('hierarchy', '?')}. {effect.get('name', 'Effect')}")
                effect_name.setStyleSheet(f"font-size: 12px; color: #e1e1e1; background: transparent; border: none;")
                effect_header_layout.addWidget(effect_name)
                effect_header_layout.addStretch()

                del_effect_btn = QPushButton("✕")
                del_effect_btn.setFixedSize(18, 18)
                del_effect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_effect_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; border: none;
                        color: #888; font-size: 11px; padding: 0px;
                    }}
                    QPushButton:hover {{ color: #e13b3e; }}
                """)
                eid = effect.get("id")
                del_effect_btn.clicked.connect(lambda _, e_id=eid: self._on_delete_effect(e_id))
                effect_header_layout.addWidget(del_effect_btn)

                effect_layout.addWidget(effect_header)

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

        if widget_type == "choice":
            widget = QComboBox()
            for value, label in entry["choices"].items():
                widget.addItem(label, value)
            widget.setCurrentIndex(max(0, widget.findData(current_value)))
            widget.setStyleSheet("background: #2a2a2a; color: #e1e1e1; border: 1px solid #3a3a3a; padding: 3px;")
            widget.currentIndexChanged.connect(lambda _, k=key, w=widget, cb=callback: cb(k, w.currentData()))
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

    def _build_project_settings(self) -> QDialog | None:
        try:
            manifest = json.loads((self._project_path / "project.json").read_text())
        except (json.JSONDecodeError, OSError):
            return None

        dialog = QDialog(self)
        dialog.setWindowTitle("Project Settings")
        form = QFormLayout(dialog)
        form.setSpacing(6)
        for entry in PROJECT_SCHEMA:
            label = QLabel(entry["label"])
            label.setStyleSheet("font-size: 12px; color: #aaa; background: transparent;")
            widget = self._make_property_widget(
                entry, manifest, lambda key, value, m=manifest: self._on_project_setting_changed(m, key, value))
            if widget is not None:
                form.addRow(label, widget)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        form.addRow(close_btn)
        return dialog

    def _on_configure_project(self):
        dialog = self._build_project_settings()
        if dialog is not None:
            dialog.exec()

    def _on_project_setting_changed(self, manifest: dict, key: str, value):
        set_nested(manifest, key, value)
        manifest["editor_version"] = AWE_VERSION
        atomic_write_json(self._project_path / "project.json", manifest)

    def _on_property_changed(self, key: str, value):
        if self._selected_layer is None:
            return
        set_nested(self._selected_layer, key, value)
        self._schedule_save_layers()
        if key == "name" or key == "visible":
            self._rebuild_layer_panel()
        if key not in self.NON_RENDER_KEYS:
            self._canvas_view.request_update()

    def _on_color_pick(self, key: str, button: QPushButton, current: str, callback=None):
        color = QColorDialog.getColor(QColor(current), self, "Pick Color")
        if not color.isValid():
            return
        hex_color = color.name()
        button.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #3a3a3a;")
        cb = callback or self._on_property_changed
        cb(key, hex_color)

    def _on_file_browse(self, key: str, line_edit: QLineEdit):
        if key == "image":
            filt = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*)"
        elif key == "video":
            filt = "Videos (*.mp4 *.webm *.mkv *.mov *.gif);;All files (*)"
        else:
            filt = "All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select File", str(Path.home()), filt)
        if not path:
            return
        src = Path(path)
        layer_id = self._selected_layer.get("id")
        dest_name = f"{layer_id}{src.suffix}"
        dest = self._project_path / "assets" / dest_name
        shutil.copy2(str(src), str(dest))
        rel = f"assets/{dest_name}"
        line_edit.setText(rel)
        self._on_property_changed(key, rel)
        self._flush_pending_saves()

    def _on_add_effect(self):
        if self._selected_layer is None:
            return
        layer_type = self._selected_layer.get("type", "")
        dialog = AddEffectDialog(self, layer_type=layer_type)
        if not dialog.exec():
            return
        selected_effect_type = dialog.get_selected_effect_type()
        if not selected_effect_type:
            return
        layer_id = self._selected_layer.get("id")
        new_effect = create_effect(self._effects, layer_id, layer_type, selected_effect_type)
        self._effects.append(new_effect)
        resolve_effect_hierarchy(self._effects, layer_id)
        self._save_effects()
        self._rebuild_inspector()
        self._canvas_view.request_update()

    def _on_delete_effect(self, effect_id: int):
        delete_effect(self._effects, effect_id)
        self._save_effects()
        self._rebuild_inspector()
        self._canvas_view.request_update()

    def _on_effect_property_changed(self, effect: dict, key: str, value):
        set_nested(effect, key, value)
        self._schedule_save_effects()
        self._canvas_view.request_update()

    def _build_status_strip(self) -> QFrame:
        strip = QFrame()
        strip.setFixedHeight(28)
        strip.setStyleSheet(f"QFrame {{ background-color: {PANEL_BG}; border-top: 1px solid {PANEL_BORDER}; }}")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        toggle_btn_style = f"""
            QPushButton {{
                background-color: {BTN_BG};
                color: #e1e1e1;
                border: 1px solid {BTN_BORDER};
                border-radius: 3px;
                font-size: 13px;
                padding: 0px;
            }}
            QPushButton:hover {{ background-color: {BTN_HOVER}; }}
            QPushButton:checked {{ background-color: {AEYIAN_BLUE}; border-color: {AEYIAN_BLUE}; }}
        """

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(28, 22)
        self._play_btn.setCheckable(True)
        self._play_btn.setStyleSheet(toggle_btn_style)
        self._play_btn.toggled.connect(self._on_play_toggled)
        layout.addWidget(self._play_btn)

        self._time_label = QLabel("t=0.00s")
        self._time_label.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        self._time_label.setMinimumWidth(60)
        layout.addWidget(self._time_label)

        self._cursor_label = QLabel("(0.50, 0.50)")
        self._cursor_label.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        self._cursor_label.setMinimumWidth(90)
        layout.addWidget(self._cursor_label)

        layout.addStretch()

        track_btn_style = f"""
            QPushButton {{
                background-color: {BTN_BG};
                color: #e1e1e1;
                border: 1px solid {BTN_BORDER};
                border-radius: 3px;
                padding: 2px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {BTN_HOVER}; }}
            QPushButton:checked {{ background-color: {AEYIAN_BLUE}; border-color: {AEYIAN_BLUE}; }}
        """

        self._track_cursor_btn = QPushButton("Track Cursor")
        self._track_cursor_btn.setCheckable(True)
        self._track_cursor_btn.setStyleSheet(track_btn_style)
        self._track_cursor_btn.toggled.connect(self._canvas_view.set_track_cursor)
        layout.addWidget(self._track_cursor_btn)

        return strip

    def _on_play_toggled(self, checked: bool):
        self._play_btn.setText("⏹" if checked else "▶")
        self._canvas_view.set_playing(checked)

    def _refresh_preview_status(self):
        self._time_label.setText(f"t={self._canvas_view._preview_time:.2f}s")
        sc = self._canvas_view._sim_cursor
        self._cursor_label.setText(f"({sc.x():.2f}, {sc.y():.2f})")

    def closeEvent(self, event):
        self._flush_pending_saves()
        preview = self._canvas_view.render_to_image()
        preview = preview.scaled(160, 90,
                                 Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation)
        if preview.width() > 160 or preview.height() > 90:
            crop_x = (preview.width() - 160) // 2
            crop_y = (preview.height() - 90) // 2
            preview = preview.copy(crop_x, crop_y, 160, 90)
        preview.save(str(self._project_path / "preview.png"))
        if "--from-awe" in sys.argv:
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

    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = CreatorWindow(project_path)
    window.show()
    sys.exit(app.exec())
