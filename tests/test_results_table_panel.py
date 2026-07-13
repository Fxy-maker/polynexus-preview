from __future__ import annotations

import math

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QTableWidget,
    QWidget,
)

from polynexus.gui import i18n
from polynexus.gui.result_table_models import (
    HeroMetric,
    ResultTableSection,
    TableCell,
    TableColumn,
)


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _panel_types():
    from polynexus.gui.widgets.results_table_panel import (
        ResultsTablePanel,
        TypedTableWidgetItem,
    )

    return ResultsTablePanel, TypedTableWidgetItem


def _section(
    *rows: tuple[TableCell, ...],
    columns: tuple[TableColumn, ...] | None = None,
) -> ResultTableSection:
    return ResultTableSection(
        columns=columns
        or (
            TableColumn("sample", "Sample"),
            TableColumn("score", "Score", unit="%", alignment="right"),
        ),
        rows=rows,
    )


def test_panel_populates_heroes_tabs_headers_and_typed_cell_roles(app: QApplication) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    primary = _section(
        (
            TableCell("sample-a", "Sample A", tooltip="Sample source"),
            TableCell(
                9.8,
                "9.8",
                status="reliable",
                tooltip="Calculated score",
                provenance="analysis.score",
            ),
        )
    )
    detail = _section((TableCell("sample-a", "Sample A"), TableCell(10.2, "10.2")))
    diagnostics = _section(
        (
            TableCell("sample-a", "Sample A"),
            TableCell(None, "No diagnostic value", status="review"),
        )
    )
    hero = HeroMetric(
        "score",
        "Score",
        9.8,
        "9.8",
        unit="%",
        status="reliable",
        tooltip="Calculated score",
        provenance="analysis.score",
    )

    panel.set_content(
        heroes=(hero,), primary=primary, detail=detail, diagnostics=diagnostics
    )

    assert panel.tabs.count() == 3
    assert [panel.tabs.widget(index) for index in range(3)] == [
        panel.primary_table,
        panel.detail_table,
        panel.diagnostic_table,
    ]
    assert panel.primary_table.objectName() == "results_primary_table"
    assert panel.detail_table.objectName() == "results_detail_table"
    assert panel.diagnostic_table.objectName() == "results_diagnostic_table"
    assert panel.primary_table.rowCount() == 1
    assert panel.primary_table.columnCount() == 2
    assert [panel.primary_table.horizontalHeaderItem(index).text() for index in range(2)] == [
        "Sample",
        "Score / %",
    ]
    score_item = panel.primary_table.item(0, 1)
    assert score_item.text() == "9.8"
    assert score_item.data(Qt.UserRole) == 9.8
    assert score_item.data(Qt.UserRole + 1) == "reliable"
    assert score_item.toolTip() == "Calculated score\nanalysis.score"
    assert score_item.textAlignment() & Qt.AlignRight
    status_label = panel.primary_table.cellWidget(0, 1).findChild(
        QLabel, "result_cell_status_reliable"
    )
    assert status_label.text() == i18n.tr("RESULTS_STATUS_RELIABLE")

    assert len(panel.hero_labels) == 1
    assert "Score" in panel.hero_labels[0].text()
    assert "9.8" in panel.hero_labels[0].text()
    assert i18n.tr("RESULTS_STATUS_RELIABLE") in panel.hero_labels[0].text()
    assert "%" in panel.hero_labels[0].text()
    assert panel.hero_labels[0].toolTip() == "Calculated score\nanalysis.score"
    assert panel.hero_labels[0].objectName() == "result_metric_reliable"
    assert not panel.findChild(QWidget, "results_metrics").isHidden()
    assert not panel.findChild(QTableWidget, "results_primary_table").isHidden()


def test_empty_optional_tabs_are_hidden_while_primary_is_always_visible(
    app: QApplication,
) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()

    panel.set_content(
        heroes=(),
        primary=ResultTableSection.empty(),
        detail=ResultTableSection.empty(),
        diagnostics=ResultTableSection.empty(),
    )

    assert panel.tabs.isTabVisible(0)
    assert not panel.tabs.isTabVisible(1)
    assert not panel.tabs.isTabVisible(2)
    metrics = panel.findChild(QWidget, "results_metrics")
    assert metrics is not None
    assert metrics.isHidden()


def test_repeated_content_replaces_old_hero_widgets_and_caps_cards_at_six(
    app: QApplication,
) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    empty = ResultTableSection.empty()
    first = HeroMetric("old", "Old", 1, "1")
    replacements = tuple(
        HeroMetric(str(index), f"Metric {index}", index, str(index)) for index in range(8)
    )

    panel.set_content(heroes=(first,), primary=empty, detail=empty, diagnostics=empty)
    old_label = panel.hero_labels[0]
    panel.set_content(
        heroes=replacements, primary=empty, detail=empty, diagnostics=empty
    )

    assert old_label.parent() is None
    assert old_label not in panel.hero_labels
    assert len(panel.hero_labels) == 6
    assert [label.text().splitlines()[0] for label in panel.hero_labels] == [
        f"Metric {index}" for index in range(6)
    ]


def test_typed_item_sorts_finite_numeric_values_numerically(app: QApplication) -> None:
    _, TypedTableWidgetItem = _panel_types()
    table = QTableWidget(2, 1)
    table.setItem(0, 0, TypedTableWidgetItem("10.2", raw=10.2, status="reliable"))
    table.setItem(1, 0, TypedTableWidgetItem("9.8", raw=9.8, status="reliable"))

    table.sortItems(0, Qt.AscendingOrder)

    assert [table.item(row, 0).data(Qt.UserRole) for row in range(2)] == [9.8, 10.2]


def test_typed_item_sorts_arbitrarily_large_integers_without_overflow(
    app: QApplication,
) -> None:
    _, TypedTableWidgetItem = _panel_types()
    smaller = 10**399
    larger = 10**400
    table = QTableWidget(2, 1)
    table.setItem(0, 0, TypedTableWidgetItem(str(larger), raw=larger))
    table.setItem(1, 0, TypedTableWidgetItem(str(smaller), raw=smaller))

    table.sortItems(0, Qt.AscendingOrder)

    assert [table.item(row, 0).data(Qt.UserRole) for row in range(2)] == [smaller, larger]


def test_typed_item_sorts_mixed_and_unavailable_values_deterministically(
    app: QApplication,
) -> None:
    _, TypedTableWidgetItem = _panel_types()
    values = [None, math.nan, "zeta", 2.5, False, "Alpha", math.inf, -3]
    table = QTableWidget(len(values), 1)
    for row, value in enumerate(values):
        table.setItem(
            row,
            0,
            TypedTableWidgetItem(str(value), raw=value, status="neutral"),
        )

    table.sortItems(0, Qt.AscendingOrder)

    sorted_values = [table.item(row, 0).data(Qt.UserRole) for row in range(len(values))]
    assert sorted_values[:3] == [-3, False, 2.5]
    assert sorted_values[3:5] == ["Alpha", "zeta"]
    assert sorted_values[5] is None
    assert math.isinf(sorted_values[6])
    assert math.isnan(sorted_values[7])


def test_tables_are_read_only_row_selecting_and_pixel_scrolling(app: QApplication) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()

    for table in (panel.primary_table, panel.detail_table, panel.diagnostic_table):
        assert table.editTriggers() == QAbstractItemView.NoEditTriggers
        assert table.selectionBehavior() == QAbstractItemView.SelectRows
        assert table.selectionMode() == QAbstractItemView.ExtendedSelection
        assert table.alternatingRowColors()
        assert not table.wordWrap()
        assert table.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel
        assert table.verticalScrollMode() == QAbstractItemView.ScrollPerPixel


def test_set_content_restores_each_tables_sorting_state(app: QApplication) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    panel.primary_table.setSortingEnabled(True)
    panel.detail_table.setSortingEnabled(False)
    panel.diagnostic_table.setSortingEnabled(True)
    section = _section((TableCell("b", "B"), TableCell(2, "2")))

    panel.set_content(
        heroes=(), primary=section, detail=section, diagnostics=section
    )

    assert panel.primary_table.isSortingEnabled()
    assert not panel.detail_table.isSortingEnabled()
    assert panel.diagnostic_table.isSortingEnabled()


def test_tab_labels_follow_language_and_restore_previous_language(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    ResultsTablePanel, _ = _panel_types()
    previous = i18n.get_language()
    monkeypatch.setattr(i18n, "_save_lang", lambda: None)
    try:
        i18n.set_language("zh")
        panel = ResultsTablePanel()
        assert [panel.tabs.tabText(index) for index in range(3)] == [
            "关键结果",
            "完整明细",
            "质量诊断",
        ]

        i18n.set_language("en")
        panel.retranslate()
        assert [panel.tabs.tabText(index) for index in range(3)] == [
            "Key results",
            "Full details",
            "Quality diagnostics",
        ]

        i18n.set_language("zh")
        panel.retranslate()
        assert [panel.tabs.tabText(index) for index in range(3)] == [
            "关键结果",
            "完整明细",
            "质量诊断",
        ]
    finally:
        i18n.set_language(previous)


def test_non_neutral_status_text_is_visible_in_both_languages(
    app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    ResultsTablePanel, _ = _panel_types()
    previous = i18n.get_language()
    monkeypatch.setattr(i18n, "_save_lang", lambda: None)
    columns = (
        TableColumn("score", "Score", alignment="right"),
        TableColumn("input", "Input"),
        TableColumn("fit", "Fit"),
    )
    primary = _section(
        (
            TableCell(0.91, "0.91", status="reliable"),
            TableCell("input-a", "Check input", status="review"),
            TableCell(None, "No fit", status="blocked"),
        ),
        columns=columns,
    )
    heroes = (
        HeroMetric("score", "Score", 0.91, "0.91", status="reliable"),
        HeroMetric("rows", "Rows", 2, "2 rows", status="review"),
        HeroMetric("runs", "Runs", 0, "0 runs", status="blocked"),
    )
    empty = ResultTableSection.empty()
    try:
        i18n.set_language("zh")
        panel = ResultsTablePanel()
        panel.set_content(
            heroes=heroes, primary=primary, detail=empty, diagnostics=empty
        )

        assert [panel.primary_table.item(0, column).text() for column in range(3)] == [
            "0.91",
            "Check input",
            "No fit",
        ]
        assert _visible_cell_statuses(panel.primary_table) == ["可靠", "需复核", "阻塞"]
        assert [label.text().splitlines()[-1] for label in panel.hero_labels] == [
            "可靠",
            "需复核",
            "阻塞",
        ]

        i18n.set_language("en")
        panel.retranslate()

        assert _visible_cell_statuses(panel.primary_table) == [
            "Reliable",
            "Review",
            "Blocked",
        ]
        assert [label.text().splitlines()[-1] for label in panel.hero_labels] == [
            "Reliable",
            "Review",
            "Blocked",
        ]
    finally:
        i18n.set_language(previous)


def _visible_cell_statuses(table: QTableWidget) -> list[str]:
    return [
        table.cellWidget(0, column)
        .findChild(QLabel, f"result_cell_status_{status}")
        .text()
        for column, status in enumerate(("reliable", "review", "blocked"))
    ]
