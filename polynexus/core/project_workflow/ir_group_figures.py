"""Conservative FTIR group figure candidates for ARS-selected groups."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterable, Mapping

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from polynexus.core.ir_engine import IRConfig, load_spectrum, preprocess_pipeline

from .models import canonical_json
from .selection import ResolvedFigureSelection


@dataclass(frozen=True)
class FigureCandidate:
    """One rendered figure plus the exact project sources behind it."""

    candidate_id: str
    kind: str
    role: str
    group_ids: tuple[str, ...]
    technique: str
    condition_kind: str
    source_artifacts: tuple[str, ...]
    paths: tuple[str, ...]
    status: str = "review_required"
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "role": self.role,
            "group_ids": list(self.group_ids),
            "technique": self.technique,
            "condition_kind": self.condition_kind,
            "source_artifacts": list(self.source_artifacts),
            "paths": list(self.paths),
            "status": self.status,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class FigureCandidateSet:
    """Rendered main candidates and explicit omissions for one selection."""

    selection_id: str
    main_candidates: tuple[FigureCandidate, ...] = ()
    supporting_candidates: tuple[FigureCandidate, ...] = ()
    omission_reasons: tuple[str, ...] = ()
    manifest_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "selection_id": self.selection_id,
            "main_candidates": [candidate.to_dict() for candidate in self.main_candidates],
            "supporting_candidates": [candidate.to_dict() for candidate in self.supporting_candidates],
            "omission_reasons": list(self.omission_reasons),
            "manifest_path": self.manifest_path,
        }


def render_ftir_group_candidates(
    *,
    selection: ResolvedFigureSelection,
    project_root: Path,
    output_dir: Path,
    metric_values: Mapping[str, float | tuple[float, str]] | None = None,
) -> FigureCandidateSet:
    """Render overlays for one ready, same-technique FTIR group selection."""
    if selection.status != "ready":
        return FigureCandidateSet(
            selection_id=selection.selection_id,
            omission_reasons=("figure_selection_blocked",),
        )
    if not selection.groups or any(group.technique != "ir" for group in selection.groups):
        return FigureCandidateSet(
            selection_id=selection.selection_id,
            omission_reasons=("figure_candidate_technique_unsupported",),
        )
    if len(selection.groups) == 2:
        return _render_ftir_group_comparison(
            selection=selection,
            project_root=project_root,
            output_dir=output_dir,
            metric_values=metric_values or {},
        )
    if len(selection.groups) != 1:
        return _write_manifest(
            FigureCandidateSet(
                selection_id=selection.selection_id,
                omission_reasons=("group_comparison_group_count_invalid",),
            ),
            output_dir,
        )

    group = selection.groups[0]
    spectra = _load_group_spectra(group.artifact_paths, group.condition_values, project_root)
    if len(spectra) < 2:
        return _write_manifest(
            FigureCandidateSet(
                selection_id=selection.selection_id,
                omission_reasons=("group_overlay_insufficient_usable_spectra",),
            ),
            output_dir,
        )
    overlap = _shared_grid(spectra)
    if overlap is None:
        return _write_manifest(
            FigureCandidateSet(
                selection_id=selection.selection_id,
                omission_reasons=("group_overlay_no_common_wavenumber_range",),
            ),
            output_dir,
        )

    main_dir = output_dir / "main"
    main_dir.mkdir(parents=True, exist_ok=True)
    paths = _render_overlay(
        main_dir,
        group.label,
        group.condition_kind,
        spectra,
        overlap,
    )
    candidate = FigureCandidate(
        candidate_id=f"{selection.selection_id}:group_overlay",
        kind="group_overlay",
        role="main_candidate",
        group_ids=(group.group_id,),
        technique="ir",
        condition_kind=group.condition_kind,
        source_artifacts=group.artifact_paths,
        paths=paths,
    )
    main_candidates = [candidate]
    omissions: list[str] = []
    trend = _render_metric_trend(
        output_dir=main_dir,
        selection=selection,
        group_label=group.label,
        condition_kind=group.condition_kind,
        condition_values=group.condition_values,
        artifact_paths=group.artifact_paths,
        metric_values=metric_values or {},
    )
    if trend is None:
        omissions.append("metric_trend_metric_unavailable")
    elif selection.request.main_figure_limit > 1:
        main_candidates.append(trend)
    else:
        omissions.append("metric_trend_main_figure_limit_reached")
    return _write_manifest(
        FigureCandidateSet(
            selection_id=selection.selection_id,
            main_candidates=tuple(main_candidates),
            omission_reasons=tuple(omissions),
        ),
        output_dir,
    )


def _render_ftir_group_comparison(
    *,
    selection: ResolvedFigureSelection,
    project_root: Path,
    output_dir: Path,
    metric_values: Mapping[str, float | tuple[float, str]],
) -> FigureCandidateSet:
    groups = selection.groups
    loaded = tuple(
        _load_group_spectra(group.artifact_paths, group.condition_values, project_root)
        for group in groups
    )
    omissions: list[str] = []
    if any(not spectra for spectra in loaded):
        return _write_manifest(
            FigureCandidateSet(
                selection_id=selection.selection_id,
                omission_reasons=("group_comparison_insufficient_usable_spectra",),
            ),
            output_dir,
        )
    all_spectra = [item for spectra in loaded for item in spectra]
    overlap = _shared_grid(all_spectra)
    if overlap is None:
        return _write_manifest(
            FigureCandidateSet(
                selection_id=selection.selection_id,
                omission_reasons=("group_comparison_no_common_wavenumber_range",),
            ),
            output_dir,
        )
    main_dir = output_dir / "main"
    main_dir.mkdir(parents=True, exist_ok=True)
    source_artifacts = tuple(path for group in groups for path in group.artifact_paths)
    candidates: list[FigureCandidate] = [
        FigureCandidate(
            candidate_id=f"{selection.selection_id}:group_comparison_overlay",
            kind="group_comparison_overlay",
            role="main_candidate",
            group_ids=tuple(group.group_id for group in groups),
            technique="ir",
            condition_kind=groups[0].condition_kind,
            source_artifacts=source_artifacts,
            paths=_render_comparison_overlay(main_dir, groups, loaded, overlap),
            limitations=("group_condition_alignment_not_assumed",),
        )
    ]
    if not _same_conditions(loaded[0], loaded[1]):
        omissions.append("comparison_conditions_unmatched")
    elif selection.request.main_figure_limit > len(candidates):
        candidates.append(
            FigureCandidate(
                candidate_id=f"{selection.selection_id}:group_difference",
                kind="group_difference",
                role="main_candidate",
                group_ids=tuple(group.group_id for group in groups),
                technique="ir",
                condition_kind=groups[0].condition_kind,
                source_artifacts=source_artifacts,
                paths=_render_group_difference(main_dir, groups, loaded, overlap),
                limitations=("difference_is_group_a_minus_group_b",),
            )
        )
    else:
        omissions.append("group_difference_main_figure_limit_reached")
    trend = _render_comparison_metric_trend(
        output_dir=main_dir,
        selection=selection,
        groups=groups,
        metric_values=metric_values,
    )
    if trend is None:
        omissions.append("metric_trend_metric_unavailable")
    elif len(candidates) < selection.request.main_figure_limit:
        candidates.append(trend)
    else:
        omissions.append("metric_trend_main_figure_limit_reached")
    return _write_manifest(
        FigureCandidateSet(
            selection_id=selection.selection_id,
            main_candidates=tuple(candidates[: selection.request.main_figure_limit]),
            omission_reasons=tuple(dict.fromkeys(omissions)),
        ),
        output_dir,
    )


def _render_comparison_overlay(
    output_dir: Path,
    groups: tuple,
    loaded: tuple[list[tuple[float, str, np.ndarray, np.ndarray]], ...],
    grid: np.ndarray,
) -> tuple[str, ...]:
    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.set_title(f"FTIR group comparison: {groups[0].label} vs {groups[1].label}")
    axis.set_xlabel("Wavenumber (cm$^{-1}$)")
    axis.set_ylabel("Normalized absorbance (a.u.)")
    colors = ("#0072B2", "#D55E00")
    unit = "C" if groups[0].condition_kind == "temperature_C" else "min"
    for group, spectra, color in zip(groups, loaded, colors, strict=True):
        for condition, _path, x, y in spectra:
            axis.plot(
                grid,
                np.interp(grid, x, y),
                linewidth=1.1,
                color=color,
                label=f"{group.label}: {condition:g} {unit}",
            )
    axis.invert_xaxis()
    axis.legend(fontsize=7)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    paths = tuple(str(output_dir / f"ftir_group_comparison.{suffix}") for suffix in ("png", "svg"))
    figure.savefig(paths[0], dpi=300)
    figure.savefig(paths[1])
    plt.close(figure)
    return paths


def _same_conditions(
    first: list[tuple[float, str, np.ndarray, np.ndarray]],
    second: list[tuple[float, str, np.ndarray, np.ndarray]],
) -> bool:
    return {item[0] for item in first} == {item[0] for item in second}


def _render_group_difference(
    output_dir: Path,
    groups: tuple,
    loaded: tuple[list[tuple[float, str, np.ndarray, np.ndarray]], ...],
    grid: np.ndarray,
) -> tuple[str, ...]:
    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.set_title(f"FTIR difference: {groups[0].label} - {groups[1].label}")
    axis.set_xlabel("Wavenumber (cm$^{-1}$)")
    axis.set_ylabel("Absorbance difference (a.u.)")
    right = {condition: (x, y) for condition, _path, x, y in loaded[1]}
    for condition, _path, x, y in loaded[0]:
        other_x, other_y = right[condition]
        axis.plot(grid, np.interp(grid, x, y) - np.interp(grid, other_x, other_y), label=f"{condition:g}")
    axis.axhline(0.0, color="#666666", linewidth=0.7)
    axis.invert_xaxis()
    axis.legend(title=groups[0].condition_kind, fontsize=8)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    paths = tuple(str(output_dir / f"ftir_group_difference.{suffix}") for suffix in ("png", "svg"))
    figure.savefig(paths[0], dpi=300)
    figure.savefig(paths[1])
    plt.close(figure)
    return paths


def _render_comparison_metric_trend(
    *,
    output_dir: Path,
    selection: ResolvedFigureSelection,
    groups: tuple,
    metric_values: Mapping[str, float | tuple[float, str]],
) -> FigureCandidate | None:
    series: list[tuple[list[float], list[float], set[str]]] = []
    for group in groups:
        values: list[float] = []
        methods: set[str] = set()
        for condition, path in zip(group.condition_values, group.artifact_paths, strict=True):
            raw = metric_values.get(path)
            if raw is None:
                return None
            if isinstance(raw, tuple):
                value, method = float(raw[0]), str(raw[1]).strip()
            else:
                value, method = float(raw), ""
            if not math.isfinite(value) or not method:
                return None
            values.append(value)
            methods.add(method)
        series.append((list(group.condition_values), values, methods))
    figure, axis = plt.subplots(figsize=(5.8, 4.0))
    for group, (conditions, values, _methods), color in zip(groups, series, ("#0072B2", "#D55E00"), strict=True):
        axis.plot(conditions, values, marker="o", linewidth=1.2, color=color, label=group.label)
    axis.set_title("FTIR crystallinity trend comparison")
    axis.set_xlabel("Temperature (C)" if groups[0].condition_kind == "temperature_C" else "Time (min)")
    axis.set_ylabel("IR crystallinity index (%)")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    paths = tuple(str(output_dir / f"ftir_group_comparison_trend.{suffix}") for suffix in ("png", "svg"))
    figure.savefig(paths[0], dpi=300)
    figure.savefig(paths[1])
    plt.close(figure)
    methods = set().union(*(methods for _, _, methods in series))
    limitations = ["metric_is_provider_reported_ir_xc_pct"]
    if len(methods) != 1:
        limitations.append("metric_methods_differ")
    else:
        limitations.append(f"metric_method:{next(iter(methods))}")
    return FigureCandidate(
        candidate_id=f"{selection.selection_id}:group_comparison_trend",
        kind="group_comparison_trend",
        role="main_candidate",
        group_ids=tuple(group.group_id for group in groups),
        technique="ir",
        condition_kind=groups[0].condition_kind,
        source_artifacts=tuple(path for group in groups for path in group.artifact_paths),
        paths=paths,
        limitations=tuple(limitations),
    )


def _load_group_spectra(
    artifact_paths: Iterable[str],
    condition_values: Iterable[float],
    project_root: Path,
) -> list[tuple[float, str, np.ndarray, np.ndarray]]:
    config = IRConfig(baseline_method="linear", smooth_method="none")
    values: list[tuple[float, str, np.ndarray, np.ndarray]] = []
    for condition, relative_path in zip(condition_values, artifact_paths, strict=True):
        source = project_root / relative_path
        try:
            spectrum = load_spectrum(str(source), config.wavenumber_range)
            if not spectrum.has_data:
                continue
            prepared = preprocess_pipeline(spectrum, config)
            x = np.asarray(prepared.wavenumber, dtype=float)
            y = np.asarray(prepared.absorbance, dtype=float)
            valid = np.isfinite(x) & np.isfinite(y)
            if valid.sum() < 2:
                continue
            order = np.argsort(x[valid])
            values.append((float(condition), relative_path, x[valid][order], y[valid][order]))
        except (OSError, TypeError, ValueError, ArithmeticError):
            continue
    return sorted(values, key=lambda item: item[0])


def _shared_grid(spectra: list[tuple[float, str, np.ndarray, np.ndarray]]) -> np.ndarray | None:
    lower = max(float(x.min()) for _, _, x, _ in spectra)
    upper = min(float(x.max()) for _, _, x, _ in spectra)
    if not math.isfinite(lower) or not math.isfinite(upper) or upper <= lower:
        return None
    point_count = min(len(x) for _, _, x, _ in spectra)
    if point_count < 2:
        return None
    return np.linspace(lower, upper, point_count)


def _render_overlay(
    output_dir: Path,
    label: str,
    condition_kind: str,
    spectra: list[tuple[float, str, np.ndarray, np.ndarray]],
    grid: np.ndarray,
) -> tuple[str, ...]:
    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.set_title(f"FTIR spectral overlay: {label}")
    axis.set_xlabel("Wavenumber (cm$^{-1}$)")
    axis.set_ylabel("Normalized absorbance (a.u.)")
    unit = "C" if condition_kind == "temperature_C" else "min"
    for condition, _path, x, y in spectra:
        axis.plot(grid, np.interp(grid, x, y), linewidth=1.1, label=f"{condition:g} {unit}")
    axis.invert_xaxis()
    axis.legend(title=condition_kind, fontsize=8)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    stem = "ftir_group_overlay"
    paths = tuple(str(output_dir / f"{stem}.{suffix}") for suffix in ("png", "svg"))
    figure.savefig(paths[0], dpi=300)
    figure.savefig(paths[1])
    plt.close(figure)
    return paths


def _render_metric_trend(
    *,
    output_dir: Path,
    selection: ResolvedFigureSelection,
    group_label: str,
    condition_kind: str,
    condition_values: tuple[float, ...],
    artifact_paths: tuple[str, ...],
    metric_values: Mapping[str, float | tuple[float, str]],
) -> FigureCandidate | None:
    if len(set(condition_values)) != len(condition_values):
        return None
    values: list[float] = []
    methods: list[str] = []
    for path in artifact_paths:
        try:
            raw = metric_values[path]
            if isinstance(raw, tuple):
                value = float(raw[0])
                method = str(raw[1]).strip()
            else:
                value = float(raw)
                method = ""
        except (KeyError, TypeError, ValueError):
            return None
        if not math.isfinite(value) or not method:
            return None
        values.append(value)
        methods.append(method)
    if len(set(methods)) != 1:
        return None
    figure, axis = plt.subplots(figsize=(5.8, 4.0))
    axis.plot(condition_values, values, marker="o", linewidth=1.2, color="#0072B2")
    axis.set_title(f"FTIR crystallinity trend: {group_label}")
    axis.set_xlabel("Temperature (C)" if condition_kind == "temperature_C" else "Time (min)")
    axis.set_ylabel("IR crystallinity index (%)")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    stem = "ftir_metric_trend"
    paths = tuple(str(output_dir / f"{stem}.{suffix}") for suffix in ("png", "svg"))
    figure.savefig(paths[0], dpi=300)
    figure.savefig(paths[1])
    plt.close(figure)
    group = selection.groups[0]
    return FigureCandidate(
        candidate_id=f"{selection.selection_id}:metric_trend",
        kind="metric_trend",
        role="main_candidate",
        group_ids=(group.group_id,),
        technique="ir",
        condition_kind=condition_kind,
        source_artifacts=artifact_paths,
        paths=paths,
        limitations=("metric_is_provider_reported_ir_xc_pct", f"metric_method:{methods[0]}"),
    )


def _write_manifest(candidates: FigureCandidateSet, output_dir: Path) -> FigureCandidateSet:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(canonical_json(candidates.to_dict()) + "\n", encoding="utf-8")
    return FigureCandidateSet(
        selection_id=candidates.selection_id,
        main_candidates=candidates.main_candidates,
        supporting_candidates=candidates.supporting_candidates,
        omission_reasons=candidates.omission_reasons,
        manifest_path=str(manifest_path),
    )


__all__ = ["FigureCandidate", "FigureCandidateSet", "render_ftir_group_candidates"]
