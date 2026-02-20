#!/usr/bin/env python3
import json
import subprocess
import shutil
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt


_HOME = Path.home()
_WHICH = shutil.which


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
        self.setWindowTitle("Aeyian Wallpaper Engine")
        self.resize(500, 500)
        
        self.folder_path = None
        self.selected_image_path = self.read_current_kde_wallpaper()
        self.config_path = _HOME / ".config" / "AWE.json" #TODO: actually use it.
        self.load_config()

    def read_current_kde_wallpaper(self):
        return None

    def load_config(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
