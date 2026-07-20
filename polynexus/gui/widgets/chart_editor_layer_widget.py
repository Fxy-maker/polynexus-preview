"""Layer-tree widgets with compatibility helpers for the legacy object API."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class LayerTreeItem(QTreeWidgetItem):
    """Tree item that accepts the legacy one-argument ``data(role)`` call."""

    def data(self, *args):
        if len(args) == 1:
            return super().data(0, args[0])
        return super().data(*args)

    def setData(self, *args):
        if len(args) == 2:
            return super().setData(0, args[0], args[1])
        return super().setData(*args)

    def text(self, *args):
        if not args:
            return super().text(0)
        return super().text(*args)

    def checkState(self, *args):
        if not args:
            return super().checkState(0)
        return super().checkState(*args)

    def setCheckState(self, *args):
        if len(args) == 1:
            return super().setCheckState(0, args[0])
        return super().setCheckState(*args)


class LayerTreeWidget(QTreeWidget):
    """Hierarchical object surface with QListWidget-compatible row helpers."""

    def _leaf_items(self):
        items = []

        def visit(item):
            role = item.data(0, Qt.UserRole + 1)
            if role != "group":
                items.append(item)
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(self.topLevelItemCount()):
            visit(self.topLevelItem(index))
        return items

    def count(self):
        return len(self._leaf_items())

    def item(self, index):
        try:
            return self._leaf_items()[int(index)]
        except (IndexError, TypeError, ValueError):
            return None

    def setCurrentRow(self, index):
        item = self.item(index)
        if item is not None:
            self.setCurrentItem(item)


__all__ = ["LayerTreeItem", "LayerTreeWidget"]
