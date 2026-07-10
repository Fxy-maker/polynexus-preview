from polynexus.gui.table_clipboard_service import (
    copy_table_selection_to_clipboard,
    build_table_tab_separated_text,
    extract_table_text_matrix,
)


class _FakeHeader:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _FakeItem:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _FakeSelection:
    def __init__(self, rows):
        self._rows = rows

    def selectedRows(self):
        return [type("Index", (), {"row": lambda self, row=row: row})() for row in self._rows]


class _FakeTable:
    def __init__(self, headers, rows, selected_rows=None):
        self._headers = headers
        self._rows = rows
        self._selected_rows = selected_rows

    def columnCount(self):
        return len(self._headers)

    def rowCount(self):
        return len(self._rows)

    def horizontalHeaderItem(self, col):
        return _FakeHeader(self._headers[col])

    def item(self, row, col):
        value = self._rows[row][col]
        return None if value is None else _FakeItem(value)

    def selectionModel(self):
        if self._selected_rows is None:
            return None
        return _FakeSelection(self._selected_rows)


def test_build_table_tab_separated_text_uses_selected_rows_when_present():
    table = _FakeTable(
        ["Name", "Value"],
        [["alpha", "1"], ["beta", "2"], ["gamma", "3"]],
        selected_rows=[2, 0],
    )

    assert build_table_tab_separated_text(table) == (
        "Name\tValue\n"
        "alpha\t1\n"
        "gamma\t3"
    )


def test_build_table_tab_separated_text_can_skip_leading_columns():
    table = _FakeTable(
        ["Checked", "Name", "Value"],
        [["x", "alpha", "1"], ["", "beta", "2"]],
        selected_rows=None,
    )

    assert build_table_tab_separated_text(table, start_column=1) == (
        "Name\tValue\n"
        "alpha\t1\n"
        "beta\t2"
    )


def test_extract_table_text_matrix_uses_selected_rows_and_all_columns():
    table = _FakeTable(
        ["A", "B"],
        [["a1", "b1"], ["a2", "b2"], ["a3", "b3"]],
        selected_rows=[1, 2],
    )

    headers, matrix = extract_table_text_matrix(table)

    assert headers == ["A", "B"]
    assert matrix == [["a2", "b2"], ["a3", "b3"]]


def test_extract_table_text_matrix_can_skip_leading_columns():
    table = _FakeTable(
        ["Checked", "Name", "Value"],
        [["x", "alpha", "1"], ["", "beta", "2"]],
        selected_rows=None,
    )

    headers, matrix = extract_table_text_matrix(table, start_column=1)

    assert headers == ["Name", "Value"]
    assert matrix == [["alpha", "1"], ["beta", "2"]]


def test_copy_table_selection_to_clipboard_returns_shape_and_sets_text(monkeypatch):
    table = _FakeTable(
        ["Name", "Value"],
        [["alpha", "1"], ["beta", "2"]],
        selected_rows=[1],
    )
    clipboard = type("Clipboard", (), {"text": "", "setText": lambda self, value: setattr(self, "text", value)})()

    class _FakeApp:
        @staticmethod
        def clipboard():
            return clipboard

    monkeypatch.setattr("PySide6.QtWidgets.QApplication", _FakeApp)

    copied, rows, cols = copy_table_selection_to_clipboard(table)

    assert copied is True
    assert rows == 1
    assert cols == 2
    assert clipboard.text == "Name\tValue\nbeta\t2"
