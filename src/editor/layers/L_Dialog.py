from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(True)
        tree.setIndentation(20)

        for category, types in LAYER_TYPES.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            tree.addTopLevelItem(category_item)
            for layer_type in types:
                child = QTreeWidgetItem([layer_type])
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                category_item.addChild(child)
            category_item.setExpanded(True)

        layout.addWidget(tree)
