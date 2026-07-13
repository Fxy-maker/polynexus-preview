from polynexus.gui.table_clipboard_service import build_table_tab_separated_text, extract_table_text_matrix


class _Item:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _Table:
    def __init__(self, headers, rows, selected=None):
        self.headers = headers
        self.rows = rows
        self.selected = selected

    def columnCount(self):
        return len(self.headers)

    def rowCount(self):
        return len(self.rows)

    def horizontalHeaderItem(self, column):
        return _Item(self.headers[column])

    def item(self, row, column):
        value = self.rows[row][column]
        return None if value is None else _Item(value)

    def selectionModel(self):
        if self.selected is None:
            return None
        selected = self.selected

        class _Selection:
            def selectedRows(self):
                return [type("Index", (), {"row": lambda self, r=r: r})() for r in selected]

        return _Selection()


def test_clipboard_text_uses_sorted_selected_rows():
    table = _Table(["Name", "Value"], [["alpha", "1"], ["beta", "2"], ["gamma", "3"]], selected=[2, 0])

    assert build_table_tab_separated_text(table) == "Name\tValue\nalpha\t1\ngamma\t3"


def test_extract_table_text_matrix_can_skip_leading_columns():
    table = _Table(["Checked", "Name", "Value"], [["x", "alpha", "1"], ["", "beta", "2"]])

    headers, rows = extract_table_text_matrix(table, start_column=1)

    assert headers == ["Name", "Value"]
    assert rows == [["alpha", "1"], ["beta", "2"]]
