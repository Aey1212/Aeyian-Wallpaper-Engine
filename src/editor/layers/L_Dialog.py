from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
)
from PySide6.QtCore import Qt


LAYER_TYPES = {
    "Basic": [
        "Image Layer",
        "Color Layer",
    ],
    "Media": [
        "Video Layer",
        "Audio Reactive Layer",
    ],
}


class AddLayerDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Layer")
        self.setFixedSize(320, 300)
        self._selected_layer_type = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(20)

        for category, types in LAYER_TYPES.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._tree.addTopLevelItem(category_item)
            for layer_type in types:
                child = QTreeWidgetItem([layer_type])
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                category_item.addChild(child)
            category_item.setExpanded(True)

        self._tree.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._tree)

        self._add_btn = QPushButton("Add Layer")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add_layer)
        layout.addWidget(self._add_btn)

    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        if not items:
            self._selected_layer_type = None
            self._add_btn.setEnabled(False)
            return

        item = items[0]
        if item.parent() is None:
            self._selected_layer_type = None
            self._add_btn.setEnabled(False)
            return

        self._selected_layer_type = item.text(0)
        self._add_btn.setEnabled(True)

    def _on_add_layer(self):
        if self._selected_layer_type is None:
            return
        self.accept()

    def get_selected_layer_type(self):
        return self._selected_layer_type


EFFECT_DIALOG_TYPES = {
    "Visual": [
        "Grayscale",
        "Gaussian Blur",
        "Cursor Distortion",
    ],
}


class AddEffectDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Effect")
        self.setFixedSize(320, 260)
        self._selected_effect_type = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(20)

        for category, types in EFFECT_DIALOG_TYPES.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._tree.addTopLevelItem(category_item)
            for effect_type in types:
                child = QTreeWidgetItem([effect_type])
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                category_item.addChild(child)
            category_item.setExpanded(True)

        self._tree.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._tree)

        self._add_btn = QPushButton("Add Effect")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add_effect)
        layout.addWidget(self._add_btn)

    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        if not items:
            self._selected_effect_type = None
            self._add_btn.setEnabled(False)
            return

        item = items[0]
        if item.parent() is None:
            self._selected_effect_type = None
            self._add_btn.setEnabled(False)
            return

        self._selected_effect_type = item.text(0)
        self._add_btn.setEnabled(True)

    def _on_add_effect(self):
        if self._selected_effect_type is None:
            return
        self.accept()

    def get_selected_effect_type(self):
        return self._selected_effect_type
