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

    panel.set_content(heroes=(hero,), primary=primary, detail=detail, diagnostics=diagnostics)

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
    panel.set_content(heroes=replacements, primary=empty, detail=empty, diagnostics=empty)

    assert old_label.parent() is None
    assert old_label not in panel.hero_labels
    assert len(panel.hero_labels) == 6
    assert [label.text().splitlines()[0] for label in panel.hero_labels] == [
        f"Metric {index}" for index in range(6)
    ]


def test_four_hero_metrics_share_one_row_and_keep_cards_light(app: QApplication) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    empty = ResultTableSection.empty()
    heroes = tuple(
        HeroMetric(str(index), f"Metric {index}", index, str(index)) for index in range(4)
    )

    panel.set_content(heroes=heroes, primary=empty, detail=empty, diagnostics=empty)

    assert panel._metrics_layout.itemAtPosition(0, 3).widget() is not None
    assert panel._metrics_layout.itemAtPosition(1, 0) is None
    assert len(panel.hero_labels) == 4
    assert "background:" in panel.hero_labels[0].styleSheet()
    assert "#222538" not in panel.hero_labels[0].styleSheet()


def test_status_cells_use_compact_badges_and_tables_stretch_last_column(
    app: QApplication,
) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    primary = _section(
        (
            TableCell(1.0, "1.0", status="review"),
            TableCell("blocked", "blocked", status="blocked"),
        ),
        columns=(
            TableColumn("score", "Score", alignment="right"),
            TableColumn("status", "Status"),
        ),
    )

    panel.set_content(
        heroes=(),
        primary=primary,
        detail=ResultTableSection.empty(),
        diagnostics=ResultTableSection.empty(),
    )

    for column, (status, translation_key) in enumerate(
        (
            ("review", "RESULTS_STATUS_REVIEW"),
            ("blocked", "RESULTS_STATUS_BLOCKED"),
        )
    ):
        status_label = panel.primary_table.cellWidget(0, column).findChild(
            QLabel, f"result_cell_status_{status}"
        )
        assert status_label.text() == i18n.tr(translation_key)
        assert "border-radius" in status_label.styleSheet()
        assert "background" in status_label.styleSheet()
        assert "border" in status_label.styleSheet()

    assert panel.primary_table.horizontalHeader().stretchLastSection()
    assert panel.detail_table.horizontalHeader().stretchLastSection()
    assert panel.diagnostic_table.horizontalHeader().stretchLastSection()


def test_review_hint_hides_when_empty_and_exposes_primary_action(
    app: QApplication,
) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    assert panel.review_hint_widget.isHidden()
    assert panel.review_hint_action.isHidden()
    assert not panel.review_hint_action.isEnabled()
    action_calls: list[str] = []

    panel.set_review_hint(
        title="当前判断",
        detail="1 帧需复核",
        next_text="先查看温度总览",
        status="review",
        action_text="查看温度总览",
        action=lambda: action_calls.append("clicked"),
    )

    assert not panel.review_hint_widget.isHidden()
    assert panel.review_hint_title.text() == "当前判断"
    assert panel.review_hint_detail.text() == "1 帧需复核"
    assert panel.review_hint_next.text() == "先查看温度总览"
    assert panel.review_hint_action.text() == "查看温度总览"
    panel.review_hint_action.click()
    assert action_calls == ["clicked"]

    panel.clear_review_hint()

    assert panel.review_hint_widget.isHidden()


def test_review_hint_retranslate_refreshes_localized_action_and_status(
    app: QApplication,
) -> None:
    ResultsTablePanel, _ = _panel_types()
    previous_language = i18n.get_language()
    try:
        i18n.set_language("en")
        panel = ResultsTablePanel()
        panel.set_review_hint(
            title="summary",
            detail="risk",
            next_text="next",
            status="review",
            action_text=i18n.tr("SAXS_RESULTS_REVIEW_HINT_ACTION"),
            action=lambda: None,
        )

        i18n.set_language("zh")
        panel.retranslate()

        assert panel.review_hint_title.text() == "summary"
        assert panel.review_hint_detail.text() == "risk"
        assert panel.review_hint_next.text() == "next"
        assert panel.review_hint_action.text() == i18n.tr("SAXS_RESULTS_REVIEW_HINT_ACTION")
        assert panel.review_hint_status.text() == i18n.tr("RESULTS_STATUS_REVIEW")
    finally:
        i18n.set_language(previous_language)


def test_review_hint_replaces_action_without_stale_callback(app: QApplication) -> None:
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    old_calls: list[str] = []
    new_calls: list[str] = []

    panel.set_review_hint(
        title="summary",
        action_text="old",
        action=lambda: old_calls.append("old"),
    )
    panel.set_review_hint(
        title="summary",
        action_text="new",
        action=lambda: new_calls.append("new"),
    )

    panel.review_hint_action.click()
    assert old_calls == []
    assert new_calls == ["new"]

    panel.clear_review_hint()
    panel._invoke_review_hint_action()
    assert old_calls == []
    assert new_calls == ["new"]


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

    panel.set_content(heroes=(), primary=section, detail=section, diagnostics=section)

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
        panel.set_content(heroes=heroes, primary=primary, detail=empty, diagnostics=empty)

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
        table.cellWidget(0, column).findChild(QLabel, f"result_cell_status_{status}").text()
        for column, status in enumerate(("reliable", "review", "blocked"))
    ]
