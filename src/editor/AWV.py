#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSize, QUrl
from PySide6.QtGui import QGuiApplication, QImage, QOffscreenSurface, QOpenGLContext
from PySide6.QtOpenGL import QOpenGLFramebufferObject
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import (
    QQuickGraphicsDevice, QQuickItem, QQuickRenderControl, QQuickRenderTarget,
    QQuickView, QQuickWindow, QSGRendererInterface,
)

SCENE_PATH = Path(__file__).resolve().parents[1] / "runtime" / "qml" / "Scene.qml"
WINDOW_SCALE = 0.5
SETTLE_TIMEOUT_S = 25.0
SETTLE_STEP_S = 0.4


def read_json(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return fallback


def load_project(project_path: Path) -> dict:
    manifest = read_json(project_path / "project.json", {})
    resolution = manifest.get("resolution", {})
    layers = read_json(project_path / "layers.json", {}).get("layers", [])
    layers.sort(key=lambda layer: layer.get("hierarchy", 0))
    for layer in layers:
        image = project_path / layer.get("image", "")
        if layer.get("image") and image.exists():
            layer["image_stamp"] = int(image.stat().st_mtime * 1000)
    return {
        "name": manifest.get("name", project_path.name),
        "width": resolution.get("width", 1920),
        "height": resolution.get("height", 1080),
        "scene": {
            "projectPath": str(project_path),
            "layers": layers,
            "effects": read_json(project_path / "effects.json", {}).get("effects", []),
        },
    }


def apply_scene(scene: QQuickItem, project: dict, cursor_x: float, cursor_y: float):
    scene.setWidth(project["width"])
    scene.setHeight(project["height"])
    for key, value in project["scene"].items():
        scene.setProperty(key, value)
    scene.setProperty("cursorX", cursor_x)
    scene.setProperty("cursorY", cursor_y)


class ViewerWindow(QQuickView):

    def __init__(self, project: dict):
        super().__init__()
        self.setTitle(f"AWV - {project['name']}")
        self.setSource(QUrl.fromLocalFile(str(SCENE_PATH)))
        self._scene = self.rootObject()
        apply_scene(self._scene, project, 0.5, 0.5)
        self._scene.setTransformOrigin(QQuickItem.TransformOrigin.TopLeft)
        self._scene.setScale(WINDOW_SCALE)
        self.resize(int(project["width"] * WINDOW_SCALE), int(project["height"] * WINDOW_SCALE))

    def mouseMoveEvent(self, event):
        if self.width() > 0 and self.height() > 0:
            x = max(0.0, min(1.0, event.position().x() / self.width()))
            y = max(0.0, min(1.0, event.position().y() / self.height()))
            self._scene.setProperty("cursorX", x)
            self._scene.setProperty("cursorY", y)
        super().mouseMoveEvent(event)


def grab_frame(project: dict, cursor_x: float, cursor_y: float) -> QImage:
    size = QSize(project["width"], project["height"])
    context = QOpenGLContext()
    context.create()
    surface = QOffscreenSurface()
    surface.setFormat(context.format())
    surface.create()
    control = QQuickRenderControl()
    window = QQuickWindow(control)
    window.setGraphicsDevice(QQuickGraphicsDevice.fromOpenGLContext(context))

    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(SCENE_PATH)))
    scene = component.create()
    scene.setParentItem(window.contentItem())
    apply_scene(scene, project, cursor_x, cursor_y)
    window.setGeometry(0, 0, size.width(), size.height())

    context.makeCurrent(surface)
    control.initialize()
    fbo = QOpenGLFramebufferObject(size, QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
    window.setRenderTarget(QQuickRenderTarget.fromOpenGLTexture(fbo.texture(), size))

    def render() -> QImage:
        QCoreApplication.processEvents()
        control.polishItems()
        control.beginFrame()
        control.sync()
        control.render()
        control.endFrame()
        context.functions().glFlush()
        return fbo.toImage()

    frame = render()
    deadline = time.monotonic() + SETTLE_TIMEOUT_S
    while time.monotonic() < deadline:
        time.sleep(SETTLE_STEP_S)
        next_frame = render()
        if next_frame == frame:
            break
        frame = next_frame
    return frame


def option_value(name: str) -> str | None:
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: AWV.py <project_path> [--grab <png>] [--cursor <x>,<y>]")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    if not (project_path / "project.json").exists():
        print(f"No project.json found in {project_path}")
        sys.exit(1)

    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    app = QGuiApplication(sys.argv)
    project = load_project(project_path)

    grab_path = option_value("--grab")
    if grab_path:
        cursor = option_value("--cursor") or "0.5,0.5"
        cursor_x, cursor_y = (float(part) for part in cursor.split(","))
        grab_frame(project, cursor_x, cursor_y).save(grab_path)
        sys.exit(0)

    window = ViewerWindow(project)
    window.show()
    sys.exit(app.exec())
