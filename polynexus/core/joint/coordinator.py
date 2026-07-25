"""JointCoordinator - unified entry point for cross-technique analysis."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import pandas as pd

from .comparators import (
    compare_crystallinity_three_way,
    compute_correlation_matrix,
    compute_ir_vs_dsc_crystallinity,
    compute_tm_vs_long_period,
    compute_xc_vs_crystallite_size,
)
from .dataset import JointBatchRow
from .matchers import MultiTechniqueTimeline
from .models import FibrillarJointModel, JointModel, LamellarJointModel
from .plotters import (
    plot_correlation_matrix,
    plot_crystallinity_comparison,
    plot_heatmap_overview,
    plot_ir_vs_dsc_xc,
    plot_timeline_alignment,
    plot_tm_vs_long_period,
    plot_xc_vs_crystallite_size,
)
from .report import make_joint_report


class JointCoordinator:
    """Cross-technique analysis dispatcher."""

    def __init__(self, sample_db=None, polymer_db=None):
        self._sample_db = sample_db
        self._polymer_db = polymer_db
        self._model_registry = {
            "lamellar": LamellarJointModel,
            "fibrillar": FibrillarJointModel,
        }

    def build_figure_definitions(self, rows: list[JointBatchRow]):
        """Build Manifest-ready figures from already-collected hub rows."""

        from .figure_provider import build_joint_figure_definitions

        return build_joint_figure_definitions(rows)

    def publish_figure_definitions(
        self,
        output_dir,
        rows: list[JointBatchRow],
        *,
        run_id: str | None = None,
    ):
        """Publish a Joint hub snapshot through the shared figure lifecycle."""

        from ..figures.production import FigureProductionPublisher

        definitions = self.build_figure_definitions(rows)
        if not definitions:
            raise ValueError("Joint publication requires at least one figure definition")
        return FigureProductionPublisher().publish(
            output_root=output_dir,
            technique="joint",
            definitions=definitions,
            run_id=run_id,
        )

    def publish_hub_report(
        self,
        rows: list[JointBatchRow],
        output_dir,
        *,
        run_id: str | None = None,
    ) -> dict:
        """Build the hub report and attach its Manifest publication context."""

        from .dataset import build_joint_hub_report

        report = build_joint_hub_report(rows)
        publication = self.publish_figure_definitions(
            output_dir,
            rows,
            run_id=run_id,
        )
        run_root = Path(output_dir).resolve() / "runs" / publication.run_id
        report["figure_publication"] = {
            "run_id": publication.run_id,
            "manifest": str(run_root / "figure_manifest.json"),
            "figure_ids": tuple(publication.primary_assets),
        }
        return report

    def compare_same_sample(self, sample_id: str, batches: list[str]) -> dict:
        """Compare results across batches of the same sample."""
        if self._sample_db is None:
            return {"error": "No SampleDB attached"}

        all_runs = []
        for bid in batches:
            runs = self._sample_db.get_analysis_runs(bid)
            all_runs.extend(runs)

        if not all_runs:
            return {"error": "No analysis runs found"}

        by_technique: dict[str, list[dict]] = {}
        for r in all_runs:
            tech = str(r.get("technique", "")).strip().lower()
            summary = r.get("results_summary", {}) or {}
            by_technique.setdefault(tech, []).append(summary)

        figures = {}
        tables = []

        if any(t in by_technique for t in ("dsc", "waxs", "saxs")):
            data = compare_crystallinity_three_way(by_technique)
            if data is not None:
                fig = plot_crystallinity_comparison(data)
                figures["crystallinity_comparison"] = fig
                tables.append(data)

        if "dsc" in by_technique and "saxs" in by_technique:
            data = compute_tm_vs_long_period(by_technique["dsc"], by_technique["saxs"])
            if data is not None:
                fig = plot_tm_vs_long_period(data)
                if fig is not None:
                    figures["tm_vs_long_period"] = fig
                    tables.append(data)

        if "dsc" in by_technique and "waxs" in by_technique:
            data = compute_xc_vs_crystallite_size(by_technique["dsc"], by_technique["waxs"])
            if data is not None:
                fig = plot_xc_vs_crystallite_size(data)
                if fig is not None:
                    figures["xc_vs_crystallite_size"] = fig
                    tables.append(data)

        if "ir" in by_technique and "dsc" in by_technique:
            data = compute_ir_vs_dsc_crystallinity(by_technique["ir"], by_technique["dsc"])
            if data is not None:
                fig = plot_ir_vs_dsc_xc(data)
                if fig is not None:
                    figures["ir_vs_dsc_xc"] = fig
                    tables.append(data)

        return make_joint_report("same_sample_comparison", figures, tables)

    def compare_cross_sample(self, sample_ids: list[str], technique: str) -> dict:
        """Compare a single technique across multiple samples."""
        if self._sample_db is None:
            return {"error": "No SampleDB attached"}

        all_summaries = []
        for sid in sample_ids:
            batches = self._sample_db.get_batches(sid)
            for b in batches:
                runs = self._sample_db.get_analysis_runs(b["id"])
                for r in runs:
                    if str(r.get("technique", "")).strip().lower() == technique:
                        s = self._sample_db.get_sample(sid)
                        summary = r.get("results_summary", {}) or {}
                        summary = dict(summary)
                        summary["_sample_name"] = s.get("polymer_name", sid) if s else sid
                        all_summaries.append(summary)

        figures = {}
        if all_summaries:
            fig = plot_heatmap_overview(all_summaries)
            if fig is not None:
                figures["heatmap_overview"] = fig

        return make_joint_report("cross_sample_comparison", figures, [])

    def correlation_matrix(
        self,
        sample_ids: list[str],
        parameters: list[str],
        method: str = "pearson",
        min_n_for_color: int = 5,
    ) -> dict:
        """Parameter correlation matrix with p-values and sample sizes."""
        if self._sample_db is None:
            return {"error": "No SampleDB attached"}

        all_params = []
        for sid in sample_ids:
            batches = self._sample_db.get_batches(sid)
            for b in batches:
                runs = self._sample_db.get_analysis_runs(b["id"])
                for r in runs:
                    summary = r.get("results_summary", {}) or {}
                    all_params.append(summary)

        if not all_params:
            return {"error": "No data"}

        df = pd.DataFrame(all_params)
        result = compute_correlation_matrix(df, parameters, method=method)

        fig = plot_correlation_matrix(result, min_n=min_n_for_color)
        figures = {"correlation_matrix": fig} if fig else {}

        return make_joint_report("correlation_matrix", figures, [result])

    def build_timeline(
        self,
        sample_id: str,
        condition_key: str,
        batches: list[str] | None = None,
    ) -> Optional[dict]:
        """Build a simple linked timeline across techniques."""
        if self._sample_db is None:
            return None

        batch_filter = set(batches or [])
        sample = self._sample_db.get_sample(sample_id)
        if not sample:
            return None

        rows = []
        timeline = MultiTechniqueTimeline(condition_key)
        for batch in self._sample_db.get_batches(sample_id):
            batch_id = batch.get("id", "")
            if batch_filter and batch_id not in batch_filter:
                continue

            condition_values = batch.get("condition_values") or {}
            if isinstance(condition_values, dict):
                condition_value = condition_values.get(condition_key)
            else:
                condition_value = None
            try:
                if condition_value is not None:
                    condition_value = float(condition_value)
            except Exception:
                pass

            for run in self._sample_db.get_analysis_runs(batch_id):
                summary = run.get("results_summary", {}) or {}
                technique = str(run.get("technique", "")).strip().lower()
                for key, value in summary.items():
                    if key.startswith("_"):
                        continue
                    if isinstance(value, (dict, list, tuple)):
                        continue

                    try:
                        numeric_value = float(value)
                    except Exception:
                        continue
                    if not math.isfinite(numeric_value):
                        continue

                    rows.append(
                        {
                            "sample_id": sample_id,
                            "sample_name": sample.get("polymer_name", sample_id),
                            "batch_id": batch_id,
                            "batch_label": batch.get("label", batch_id),
                            "condition_key": condition_key,
                            "condition_value": condition_value,
                            "technique": technique,
                            "technique_label": str(technique).upper(),
                            "param_key": key,
                            "value": numeric_value,
                        }
                    )

                    timeline.add_series(
                        {
                            "batch_id": batch_id,
                            "batch_label": batch.get("label", batch_id),
                            "sample_id": sample_id,
                            "sample_name": sample.get("polymer_name", sample_id),
                            "technique": technique,
                        },
                        param_key=key,
                        condition_values=[condition_value] if condition_value is not None else [],
                        param_values=[numeric_value],
                    )

        if not rows:
            return None

        df = pd.DataFrame(rows)
        aligned_df = timeline.to_dataframe()
        figures = {}
        if aligned_df is not None and not aligned_df.empty:
            fig = plot_timeline_alignment(aligned_df)
            if fig is not None:
                figures["timeline_alignment"] = fig
        return make_joint_report(
            "linked_timeline",
            figures,
            [df, aligned_df],
        )

    def joint_fit(
        self,
        model_name: str,
        sample_id: str,
        batch_ids: list[str],
        observations: dict,
        **kw,
    ) -> Optional[dict]:
        """Joint fitting of multi-technique data to a unified model."""
        model_cls = self._model_registry.get(str(model_name).strip().lower())
        if model_cls is None:
            return {
                "error": f"Unknown model: {model_name}",
                "available_models": self.list_models(),
            }

        model: JointModel = model_cls()
        for key, value in (observations or {}).items():
            if isinstance(value, dict):
                obs_value = value.get("value")
                obs_sigma = value.get("uncertainty", 1.0)
            elif isinstance(value, (list, tuple)) and len(value) >= 2:
                obs_value, obs_sigma = value[0], value[1]
            else:
                obs_value, obs_sigma = value, 1.0

            try:
                model.add_observation(key, obs_value, obs_sigma)
            except Exception:
                continue

        result = model.solve(method=kw.get("method", "least_squares"))
        return {
            "name": "joint_fit",
            "model": model_name,
            "sample_id": sample_id,
            "batch_ids": list(batch_ids or []),
            "success": result.success,
            "summary": result.message,
            "parameters": result.parameters,
            "residuals": result.residuals,
            "objective": result.objective,
            "n_observations": result.n_observations,
            "n_constraints": result.n_constraints,
            "details": result.details,
        }

    def list_models(self) -> list[str]:
        return sorted(self._model_registry.keys())

    def get_model_schema(self, model_name: str) -> dict:
        model_cls = self._model_registry.get(str(model_name).strip().lower())
        if model_cls is None:
            return {
                "name": model_name,
                "available_models": self.list_models(),
                "parameters": [],
                "observations": [],
                "constraints": [],
            }

        model = model_cls()
        return {
            "name": model_name,
            "parameters": [
                {
                    "name": name,
                    "initial": init,
                    "bounds": bounds,
                }
                for name, (init, bounds) in model._parameters.items()
            ],
            "observations": list(model._observations.keys()) or [
                "Tm_DSC_C",
                "L_nm",
                "Xc_pct",
                "D_Scherrer_nm",
            ],
            "constraints": [
                {"index": i, "hard": hard, "weight": weight}
                for i, (_, weight, hard) in enumerate(model._constraints)
            ],
        }
