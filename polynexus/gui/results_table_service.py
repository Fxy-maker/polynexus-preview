"""Pure helpers for building results-table models for the GUI."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .i18n import tr
from .analysis_results_table_service import build_analysis_results_presentation
from .joint_results_table_service import build_joint_results_presentation
from .result_table_models import HeroMetric, ResultTableSection, TableCell, TableColumn
from .scientific_review_presentation import ScientificReviewDisplay, scientific_review_display
from .results_workbench_profiles import profile_for
from .saxs_results_table_service import build_saxs_results_presentation
from ..core.project_workflow.result_table import GroupResultTable


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultsTableModel:
    kind: str
    columns: list[str]
    display_rows: list[list[str]]
    stored_rows: list[list[Any]]
    summary_count: int = 0
    export_enabled: bool = False
    copy_enabled: bool = False
    sortable: bool = False
    summary_kind: str = ""
    hero_metrics: tuple[HeroMetric, ...] = ()
    primary_section: ResultTableSection | None = None
    detail_section: ResultTableSection | None = None
    diagnostic_section: ResultTableSection | None = None
    risk_text: str = ""
    next_text: str = ""
    scientific_review: ScientificReviewDisplay = field(default_factory=ScientificReviewDisplay, compare=False)
    profile: Any = None


def _group_table(value: Any) -> GroupResultTable | None:
    if isinstance(value, GroupResultTable):
        return value
    if isinstance(value, dict):
        try:
            return GroupResultTable.from_dict(value)
        except (TypeError, ValueError, KeyError):
            logger.warning("Invalid group result table; using generic results table.", exc_info=True)
    return None


def build_group_results_table_model(
    table: GroupResultTable | dict[str, Any],
    *,
    language: str = "en",
) -> ResultsTableModel:
    """Adapt the shared group-table DTO for the GUI result workbench.

    The adapter only formats persisted rows/statistics. It never infers a
    condition axis or performs a scientific calculation in the GUI layer.
    """
    group = _group_table(table)
    if group is None:
        raise ValueError("group result table is invalid")
    metric_keys = sorted({str(key) for row in group.rows for key in row.metrics})
    columns = ["row_id", "source", "condition_key", "condition_value", *metric_keys, "warnings"]
    display_rows: list[list[str]] = []
    stored_rows: list[list[Any]] = []
    primary_rows: list[tuple[TableCell, ...]] = []
    for row in group.rows:
        values: list[Any] = [row.row_id, row.source, row.condition_key, row.condition_value]
        values.extend(row.metrics.get(key, "") for key in metric_keys)
        values.append(";".join(row.warnings))
        stored_rows.append(values)
        display_rows.append([_format_display_value(value, digits=4) for value in values])
        primary_rows.append(tuple(
            TableCell(raw=value, display=_format_display_value(value, digits=4), status="review" if row.warnings and index == len(values) - 1 else "neutral", provenance=row.source)
            for index, value in enumerate(values)
        ))

    stat_columns = ["condition_key", "condition_value", "metric_key", "count", "mean", "std", "cv", "minimum", "maximum", "source_row_ids"]
    stat_rows: list[tuple[TableCell, ...]] = []
    for stat in group.statistics():
        source_ids = ";".join(stat.source_row_ids)
        values = [stat.condition_key, stat.condition_value, stat.metric_key, stat.count, stat.mean, stat.std, stat.cv, stat.minimum, stat.maximum, source_ids]
        stat_rows.append(tuple(TableCell(raw=value, display=_format_display_value(value, digits=4), provenance=";".join(stat.source_row_ids)) for value in values))

    warning_columns = ["row_id", "source", "warning"]
    warning_rows = [
        tuple(TableCell(raw=value, display=str(value), status="review", provenance=row.source) for value in (row.row_id, row.source, warning))
        for row in group.rows for warning in row.warnings
    ]
    primary = ResultTableSection(
        columns=tuple(TableColumn(key=key, label=key) for key in columns),
        rows=tuple(primary_rows),
    )
    detail = ResultTableSection(
        columns=tuple(TableColumn(key=key, label=key) for key in stat_columns),
        rows=tuple(stat_rows),
    )
    diagnostics = ResultTableSection(
        columns=tuple(TableColumn(key=key, label=key) for key in warning_columns),
        rows=tuple(warning_rows),
    )
    return ResultsTableModel(
        kind="group",
        columns=columns,
        display_rows=display_rows,
        stored_rows=stored_rows,
        summary_count=len(group.rows),
        export_enabled=bool(group.rows),
        copy_enabled=bool(group.rows),
        sortable=bool(group.rows),
        summary_kind="group",
        primary_section=primary,
        detail_section=detail,
        diagnostic_section=diagnostics,
    )


def _format_display_value(value, *, digits: int) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _qualified_saxs_submodule(submodule: str) -> str:
    normalized = str(submodule or "").strip().lower()
    if normalized in {"", "saxs"}:
        return "saxs.static"
    if normalized.startswith("saxs."):
        return normalized
    return f"saxs.{normalized}"


def _saxs_summary_kind(params: Any) -> str:
    if not isinstance(params, dict):
        return "single"
    if "_batch_data" in params:
        return "batch"
    batch_frames = params.get("batch_frames", 0)
    try:
        return "batch" if batch_frames > 1 else "single"
    except TypeError:
        return "single"


_ANALYSIS_SUBMODULES = {
    "dsc": {
        "dsc.standard",
        "dsc.isothermal",
        "dsc.nonisothermal",
    },
    "ir": {
        "ir.standard",
        "ir.mapping",
        "ir.temperature_2d",
    },
    "waxs": {
        "waxs.static",
        "waxs.temperature",
        "waxs.strain",
    },
    "nmr": {
        "nmr.liquid_h",
        "nmr.liquid_c",
        "nmr.solid_h",
        "nmr.solid_c",
    },
}


def _qualified_analysis_submodule(technique: str, submodule: str) -> str:
    tech = str(technique or "").strip().lower()
    normalized = str(submodule or "").strip().lower()
    if not normalized:
        return {
            "dsc": "dsc.standard",
            "ir": "ir.standard",
            "waxs": "waxs.static",
            "nmr": "nmr.solid_h",
        }.get(tech, "")
    if normalized == tech:
        return {
            "dsc": "dsc.standard",
            "ir": "ir.standard",
            "waxs": "waxs.static",
            "nmr": "nmr.solid_h",
        }.get(tech, "")
    if normalized.startswith(f"{tech}."):
        return normalized
    return f"{tech}.{normalized}"


def _analysis_submodule_supported(technique: str, submodule: str) -> bool:
    tech = str(technique or "").strip().lower()
    normalized = _qualified_analysis_submodule(tech, submodule)
    return normalized in _ANALYSIS_SUBMODULES.get(tech, set())


def _analysis_summary_kind(params: Any) -> str:
    if not isinstance(params, dict):
        return "single"
    if isinstance(params.get("_batch_data"), list):
        return "batch"
    try:
        return "batch" if int(params.get("batch_frames", 0) or 0) > 1 else "single"
    except (TypeError, ValueError):
        return "single"


def build_results_table_model(
    params,
    *,
    ordered_columns_fn: Callable[[list[str]], list[str]],
    flatten_params_fn: Callable[[Any], list[tuple[str, Any]]],
    technique: str = "",
    submodule: str = "",
    language: str = "en",
    review_source: Any = None,
    group_table: GroupResultTable | dict[str, Any] | None = None,
) -> ResultsTableModel:
    selected_group_table = _group_table(group_table)
    if selected_group_table is None and isinstance(params, dict):
        selected_group_table = _group_table(params.get("group_result_table"))
    if selected_group_table is not None:
        return build_group_results_table_model(selected_group_table, language=language)
    review_display = scientific_review_display(
        params if review_source is None else review_source,
        technique=technique,
        submodule=submodule,
        language=language,
    )
    if isinstance(params, dict) and len(params) > 1 and all(isinstance(v, dict) for v in params.values()) and not any(
        str(k).startswith("_") for k in params
    ):
        sample_labels = list(params.keys())
        all_keys: list[str] = []
        for values in params.values():
            for key in values:
                if key not in all_keys:
                    all_keys.append(key)
        columns = ordered_columns_fn(["sample", *all_keys])
        display_rows: list[list[str]] = []
        stored_rows: list[list[Any]] = []
        for label in sample_labels:
            values = params[label]
            display_row = [str(label)]
            stored_row = [label]
            for key in columns[1:]:
                value = values.get(key, "")
                stored_row.append(value)
                display_row.append(_format_display_value(value, digits=2))
            display_rows.append(display_row)
            stored_rows.append(stored_row)
        return ResultsTableModel(
            kind="multi_sample",
            columns=columns,
            display_rows=display_rows,
            stored_rows=stored_rows,
            summary_count=len(sample_labels),
            export_enabled=True,
            copy_enabled=True,
            sortable=True,
            summary_kind="multi_sample",
            scientific_review=review_display,
        )

    if str(technique or "").strip().lower() == "saxs":
        try:
            presentation = build_saxs_results_presentation(
                params if isinstance(params, dict) else {},
                submodule=_qualified_saxs_submodule(submodule),
                language=language,
            )
        except Exception:
            logger.warning(
                "SAXS structured results presentation failed; using generic results table.",
                exc_info=True,
            )
        else:
            primary = presentation.primary
            return ResultsTableModel(
                kind=presentation.kind,
                columns=[column.header for column in primary.columns],
                display_rows=[
                    [cell.display for cell in row]
                    for row in primary.rows
                ],
                stored_rows=[
                    [cell.raw for cell in row]
                    for row in primary.rows
                ],
                summary_count=presentation.summary_count,
                export_enabled=presentation.export_enabled,
                copy_enabled=presentation.copy_enabled,
                sortable=presentation.sortable,
                summary_kind=_saxs_summary_kind(params),
                hero_metrics=presentation.hero_metrics,
                primary_section=primary,
                detail_section=presentation.detail,
                diagnostic_section=presentation.diagnostics,
                risk_text=presentation.risk_text,
                next_text=presentation.next_text,
                profile=profile_for(presentation.kind, language=language),
                scientific_review=review_display,
            )

    normalized_technique = str(technique or "").strip().lower()
    if normalized_technique == "joint":
        presentation = build_joint_results_presentation(params, language=language)
        primary = presentation.primary
        return ResultsTableModel(
            kind=presentation.kind,
            columns=[column.header for column in primary.columns],
            display_rows=[[cell.display for cell in row] for row in primary.rows],
            stored_rows=[[cell.raw for cell in row] for row in primary.rows],
            summary_count=presentation.summary_count,
            export_enabled=presentation.export_enabled,
            copy_enabled=presentation.copy_enabled,
            sortable=presentation.sortable,
            summary_kind="joint",
            hero_metrics=presentation.hero_metrics,
            primary_section=primary,
            detail_section=presentation.detail,
            diagnostic_section=presentation.diagnostics,
            risk_text=presentation.risk_text,
            next_text=presentation.next_text,
            profile=profile_for("joint", language=language),
            scientific_review=review_display,
        )

    if normalized_technique in _ANALYSIS_SUBMODULES and _analysis_submodule_supported(
        normalized_technique,
        submodule,
    ):
        qualified_submodule = _qualified_analysis_submodule(normalized_technique, submodule)
        try:
            presentation = build_analysis_results_presentation(
                params,
                technique=normalized_technique,
                submodule=qualified_submodule,
                language=language,
            )
        except Exception:
            logger.warning(
                "Analysis results presentation failed; using generic results table.",
                exc_info=True,
            )
        else:
            if presentation is not None:
                primary = presentation.primary
                return ResultsTableModel(
                    kind=presentation.kind,
                    columns=[column.header for column in primary.columns],
                    display_rows=[[cell.display for cell in row] for row in primary.rows],
                    stored_rows=[[cell.raw for cell in row] for row in primary.rows],
                    summary_count=presentation.summary_count,
                    export_enabled=presentation.export_enabled,
                    copy_enabled=presentation.copy_enabled,
                    sortable=presentation.sortable,
                    summary_kind=_analysis_summary_kind(params),
                    hero_metrics=presentation.hero_metrics,
                    primary_section=primary,
                    detail_section=presentation.detail,
                    diagnostic_section=presentation.diagnostics,
                    risk_text=presentation.risk_text,
                    next_text=presentation.next_text,
                    profile=profile_for(presentation.kind, language=language),
                    scientific_review=review_display,
                )

    batch_frames = params.get("batch_frames", 0) if isinstance(params, dict) else 0
    if isinstance(params, dict) and batch_frames > 1 and "_batch_data" in params:
        batch_data = params["_batch_data"] if isinstance(params.get("_batch_data"), list) else []
        all_keys: list[str] = []
        for row in batch_data:
            if not isinstance(row, dict):
                continue
            for key in row:
                if key not in all_keys:
                    all_keys.append(key)
        columns = ordered_columns_fn(all_keys if all_keys else ["file", "L_nm", "lc_nm", "Xc"])
        display_rows = []
        stored_rows = []
        for row in batch_data:
            row = row if isinstance(row, dict) else {}
            display_row = []
            stored_row = []
            for key in columns:
                value = row.get(key, "")
                stored_row.append(value)
                display_row.append(_format_display_value(value, digits=3))
            display_rows.append(display_row)
            stored_rows.append(stored_row)
        return ResultsTableModel(
            kind="batch",
            columns=columns,
            display_rows=display_rows,
            stored_rows=stored_rows,
            summary_count=len(batch_data) or int(batch_frames or 0),
            export_enabled=True,
            copy_enabled=True,
            sortable=True,
            summary_kind="batch",
            scientific_review=review_display,
        )

    items = flatten_params_fn(params)
    columns = [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")]
    display_rows = [[str(key), _format_display_value(value, digits=4)] for key, value in items]
    stored_rows = [[key, value] for key, value in items]
    has_items = bool(items)
    return ResultsTableModel(
        kind="single",
        columns=columns,
        display_rows=display_rows,
        stored_rows=stored_rows,
        summary_count=len(items),
        export_enabled=has_items,
        copy_enabled=has_items,
        sortable=False,
        summary_kind="single",
        scientific_review=review_display,
    )


def build_batch_results_table_model(
    all_results,
    *,
    ordered_columns_fn: Callable[[list[str]], list[str]],
) -> ResultsTableModel:
    all_keys: list[str] = []
    flat_rows: list[dict[str, Any]] = []

    for row in all_results if isinstance(all_results, list) else []:
        if not isinstance(row, dict):
            continue
        flat: dict[str, Any] = {}
        file_name = row.get("file", "")
        flat["file"] = file_name
        params = row.get("params", {})
        if isinstance(params, dict):
            for key, val in params.items():
                if isinstance(val, dict):
                    flat.update(val)
                else:
                    flat[key] = val
        for key in flat:
            if key not in all_keys:
                all_keys.append(key)
        flat_rows.append(flat)

    columns = ordered_columns_fn(all_keys)
    display_rows: list[list[str]] = []
    stored_rows: list[list[Any]] = []
    for flat in flat_rows:
        display_row: list[str] = []
        stored_row: list[Any] = []
        for key in columns:
            value = flat.get(key, "")
            stored_row.append(value)
            display_row.append(_format_display_value(value, digits=4))
        display_rows.append(display_row)
        stored_rows.append(stored_row)

    has_rows = bool(flat_rows)
    return ResultsTableModel(
        kind="batch",
        columns=columns,
        display_rows=display_rows,
        stored_rows=stored_rows,
        summary_count=len(flat_rows),
        export_enabled=has_rows,
        copy_enabled=has_rows,
        sortable=has_rows,
        summary_kind="batch",
    )
