"""Immutable ARS-facing evidence package materialization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import os
import re
import shutil
import tempfile
import math
from typing import Any, Iterable, Mapping

from polynexus.core.agent_workflow.models import AnalysisRun

from .evidence import ProjectWorkflowRun
from .ir_group_figures import FigureCandidateSet
from .models import EvidenceItem, canonical_json
from .writing_metrics import CitationMetric, extract_package_metrics, with_package_assets
from .ars_handoff import build_ars_writing_input
from .workspace import ProjectWorkspace


_VERSION_RE = re.compile(r"^(?P<name>.+)-v(?P<version>\d{3,})$")
_FIGURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".svg", ".pdf", ".tif", ".tiff"})
_TABLE_SUFFIXES = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".json"})


@dataclass(frozen=True)
class ResearchEvidencePackage:
    """Materialized package snapshot and its stable identity."""

    package_id: str
    version: int
    path: Path
    status: str
    package_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "version": self.version,
            "path": str(self.path),
            "status": self.status,
            "package_hash": self.package_hash,
        }


class ProjectEvidencePackager:
    """Create versioned snapshots from validated project workflow runs."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        self.workspace = workspace

    def create(
        self,
        runs: Iterable[ProjectWorkflowRun],
        *,
        relations: Iterable[Mapping[str, Any]] = (),
        package_id: str = "pa6-crystallization",
        figure_candidates: FigureCandidateSet | None = None,
    ) -> ResearchEvidencePackage:
        run_values = tuple(runs)
        if not run_values:
            raise ValueError("at least one run is required")
        if not package_id or "/" in package_id or "\\" in package_id or package_id in {".", ".."}:
            raise ValueError("package_id must be a simple name")

        manifests: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        copied_assets: list[dict[str, str]] = []
        statuses: list[str] = []
        limitations: list[str] = []
        for run in run_values:
            manifest = self._validate_run(run)
            manifests.append(manifest)
            statuses.append(run.status)
            evidence.extend(item.to_dict() for item in run.evidence_items)
            limitations.extend(run.reason_codes)
            if run.analysis_run is not None and run.analysis_run.evidence is not None:
                limitations.extend(run.analysis_run.evidence.disallowed_conclusions)
            for item in run.evidence_items:
                limitations.extend(item.limitations)

            copied_assets.extend(
                self._asset_descriptors(run, package_id)
            )

        figure_candidate_payload = figure_candidates.to_dict() if figure_candidates else None
        if figure_candidates:
            copied_assets.extend(self._candidate_asset_descriptors(figure_candidates))
        copied_assets = self._disambiguate_assets(copied_assets)
        copied_assets, figure_index = self._canonical_figure_assets(copied_assets, evidence)
        if figure_candidates and figure_candidate_payload is not None:
            figure_candidate_payload = self._package_figure_candidate_payload(
                figure_candidate_payload, copied_assets
            )

        relation_values = [dict(value) for value in relations]
        if not relation_values:
            relation_values = [
                {
                    "type": "run_part_of_request",
                    "run_id": run.run_id,
                    "request_hash": run.request_hash,
                    "evidence_scope": "explicit_project_request",
                }
                for run in run_values
            ]
            techniques = sorted({item.technique for run in run_values for item in run.evidence_items})
            if len(run_values) > 1:
                relation_values.append({
                    "type": "cross_technique_evidence_set" if len(techniques) > 1 else "technique_series_evidence_set",
                    "run_ids": [run.run_id for run in run_values],
                    "techniques": techniques,
                    "evidence_scope": "explicit_package_membership",
                })
        status = "review_required" if any(value == "review_required" for value in statuses) else "completed"
        if any(value not in {"completed", "review_required"} for value in statuses):
            raise ValueError("only completed or review_required runs may be packaged")
        limitations = list(dict.fromkeys(str(value) for value in limitations if value))
        version = self._next_version(package_id)
        package_path = self.workspace.evidence_dir / f"{package_id}-v{version:03d}"
        package_path.mkdir(parents=True, exist_ok=False)
        try:
            (package_path / "figures").mkdir()
            (package_path / "tables").mkdir()
            package_manifest = {
                "package_id": package_id,
                "version": version,
                "status": status,
                "run_ids": [run.run_id for run in run_values],
                "questions": list(dict.fromkeys(
                    str(manifest.get("question", "")) for manifest in manifests if manifest.get("question")
                )),
                "run_manifests": [str(run.manifest_path) for run in run_values],
                "source_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("source_hashes", ())}),
                "canonical_template_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("canonical_template_hashes", ())}),
                "conversion_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("conversion_hashes", ())}),
                "evidence_count": len(evidence),
                "asset_count": len(copied_assets),
                "figure_count": len(figure_index["figures"]),
                "figure_index": "figure-index.json",
                "figure_candidates": figure_candidate_payload,
                "evidence_item_hashes": [
                    str(item.get("item_hash", "")) for item in evidence
                ],
                "relations_hash": hashlib.sha256(
                    canonical_json({"relations": relation_values}).encode("utf-8")
                ).hexdigest(),
                "asset_hashes": self._asset_hashes(copied_assets),
                "limitations": limitations,
            }
            technique_index = self._technique_index(run_values, evidence, limitations)
            package_manifest["techniques"] = technique_index
            citation_metrics = self._package_metrics(
                extract_package_metrics(evidence), copied_assets
            )
            writing_evidence = self._writing_evidence(
                evidence, technique_index, copied_assets, citation_metrics
            )
            ars_writing_input = build_ars_writing_input(
                package_manifest=package_manifest,
                writing_evidence=writing_evidence,
                citation_metrics={"records": [record.to_dict() for record in citation_metrics]},
                limitations={"limitations": limitations},
            )
            package_manifest["writing_evidence"] = "writing-evidence.json"
            package_manifest["citation_metrics"] = "citation-metrics.json"
            package_manifest["ars_writing_input"] = "ars-writing-input.json"
            self._write_json(package_path / "evidence.json", {"items": evidence})
            self._write_json(package_path / "relations.json", {"relations": relation_values})
            self._write_json(package_path / "techniques.json", {"techniques": technique_index})
            self._write_json(package_path / "citation-metrics.json", {
                "version": 1,
                "records": [record.to_dict() for record in citation_metrics],
                "omissions": [],
            })
            self._write_json(package_path / "writing-evidence.json", writing_evidence)
            self._write_json(package_path / "ars-writing-input.json", ars_writing_input)
            self._write_json(package_path / "limitations.json", {"limitations": limitations})
            self._copy_assets(copied_assets, package_path)
            self._write_figure_index(package_path, figure_index)
            if figure_candidate_payload is not None:
                self._write_json(package_path / "figure-candidates.json", figure_candidate_payload)
            self._write_text(
                package_path / "writing-input.md",
                self._writing_input(package_manifest, evidence, limitations, writing_evidence),
            )
            package_manifest["artifact_hashes"] = self._package_artifact_hashes(package_path)
            package_hash = hashlib.sha256(canonical_json(package_manifest).encode("utf-8")).hexdigest()
            package_manifest["package_hash"] = package_hash
            self._write_json(package_path / "manifest.json", package_manifest)
        except Exception:
            shutil.rmtree(package_path, ignore_errors=True)
            raise
        return ResearchEvidencePackage(package_id, version, package_path, status, package_hash)

    @staticmethod
    def _canonical_figure_assets(
        assets: list[dict[str, Any]], evidence: list[dict[str, Any]]
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Keep one SVG asset per directly rendered logical figure."""
        figures = [item for item in assets if item["kind"] == "figures"]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in figures:
            grouped.setdefault(
                str(item.get("logical_figure_key") or Path(item["source"]).parent), []
            ).append(item)
        retained = [item for item in assets if item["kind"] != "figures"]
        index_entries: list[dict[str, Any]] = []
        for _source_key, values in grouped.items():
            svg = next((item for item in values if Path(item["source"]).suffix.lower() == ".svg"), None)
            if svg is None:
                retained.extend(values)
                continue
            retained.append(svg)
            safe_id = Path(svg["name"]).with_suffix("").name
            metadata = f"figures/{Path(svg['name']).with_suffix('').name}.metadata.json"
            index_entries.append({
                "id": safe_id,
                "role": str(svg.get("role") or "diagnostic"),
                "technique": str(svg.get("technique") or "UNKNOWN").upper(),
                "group": str(svg.get("group") or "").strip() or None,
                "writing_eligibility": str(svg.get("writing_eligibility") or "review_only"),
                "svg": f"figures/{svg['name']}",
                "document": None,
                "data": None,
                "metadata": metadata,
            })
        return retained, {"version": 1, "figures": index_entries}

    def _write_figure_index(self, package_path: Path, payload: Mapping[str, Any]) -> None:
        self._write_json(package_path / "figure-index.json", dict(payload))
        for entry in payload.get("figures", ()):
            if not isinstance(entry, Mapping):
                continue
            self._write_json(package_path / str(entry["metadata"]), {
                "figure_id": entry["id"],
                "technique": entry["technique"],
                "role": entry["role"],
                "svg": entry["svg"],
                "document": entry["document"],
                "data": entry["data"],
            })

    @staticmethod
    def _technique_index(
        runs: tuple[ProjectWorkflowRun, ...],
        evidence: list[dict[str, Any]],
        limitations: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Project explicit run membership into an ARS-friendly technique index."""
        result: dict[str, dict[str, Any]] = {}
        for run in runs:
            techniques = sorted({item.technique for item in run.evidence_items})
            for technique in techniques:
                entry = result.setdefault(
                    technique,
                    {"run_ids": [], "evidence_count": 0, "statuses": [], "limitations": []},
                )
                if run.run_id not in entry["run_ids"]:
                    entry["run_ids"].append(run.run_id)
                entry["statuses"].append(run.status)
                matching = [
                    item for item in evidence
                    if item.get("technique") == technique
                    and run.run_id in item.get("source_runs", ())
                ]
                entry["evidence_count"] += len(matching)
                entry["limitations"].extend(item.get("limitations", ()) for item in matching)
        for entry in result.values():
            entry["statuses"] = list(dict.fromkeys(entry["statuses"]))
            entry["limitations"] = list(dict.fromkeys(
                value for values in entry["limitations"] for value in (values if isinstance(values, list) else [values]) if value
            ))
        return result

    @staticmethod
    def _writing_evidence(
        evidence: list[dict[str, Any]],
        technique_index: Mapping[str, Any],
        assets: list[dict[str, str]],
        citation_metrics: Iterable[CitationMetric] = (),
    ) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = {str(key): [] for key in technique_index}
        asset_paths = {
            str(item["source"]): f"{item['kind']}/{item['name']}" for item in assets
        }
        metric_by_evidence: dict[str, list[CitationMetric]] = {}
        for metric in citation_metrics:
            metric_by_evidence.setdefault(metric.evidence_id, []).append(metric)
        for item in evidence:
            technique = str(item.get("technique", "unknown")).lower()
            metrics = metric_by_evidence.get(str(item.get("evidence_id", "")), [])
            eligibility_counts: dict[str, int] = {}
            for metric in metrics:
                eligibility_counts[metric.writing_eligibility] = (
                    eligibility_counts.get(metric.writing_eligibility, 0) + 1
                )
            grouped.setdefault(technique, []).append({
                "evidence_id": item.get("evidence_id"),
                "status": item.get("status", "unknown"),
                "claim_scope": item.get("claim_scope", ""),
                "source_runs": list(item.get("source_runs", ())),
                "raw_sources": list(item.get("raw_sources", ())),
                "figures": [asset_paths[path] for path in item.get("figures", ()) if path in asset_paths],
                "tables": [asset_paths[path] for path in item.get("tables", ()) if path in asset_paths],
                "supported_interpretations": list(item.get("supported_interpretations", ())),
                "disallowed_conclusions": list(item.get("disallowed_conclusions", ())),
                "limitations": list(item.get("limitations", ())),
                "observed_results": item.get("observed_results", {}),
                "observed_metrics": ProjectEvidencePackager._observed_metrics(item.get("observed_results", {})),
                "citation_metric_ids": [metric.metric_id for metric in metrics],
                "citation_metric_counts": eligibility_counts,
            })
        return {"version": 1, "techniques": {
            technique: {
                "run_ids": list(technique_index.get(technique, {}).get("run_ids", ())),
                "statuses": list(technique_index.get(technique, {}).get("statuses", ())),
                "evidence": values,
            }
            for technique, values in grouped.items()
        }}

    @staticmethod
    def _package_metrics(
        metrics: Iterable[CitationMetric], assets: list[dict[str, str]]
    ) -> tuple[CitationMetric, ...]:
        """Rewrite source asset paths so all ledger links are package-relative."""
        asset_paths = {
            str(item["source"]): f"{item['kind']}/{item['name']}" for item in assets
        }
        return with_package_assets(metrics, asset_paths)

    @staticmethod
    def _observed_metrics(value: Any) -> dict[str, float | int]:
        """Extract finite scalar values without interpreting their meaning."""
        result: dict[str, float | int] = {}
        if not isinstance(value, Mapping):
            return result
        summaries = value.get("result_summary", value)
        if not isinstance(summaries, Mapping):
            return result
        for key, raw in summaries.items():
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                continue
            if isinstance(raw, float) and not math.isfinite(raw):
                continue
            result[str(key)] = raw
        return result

    def _validate_run(self, run: ProjectWorkflowRun) -> dict[str, Any]:
        if run.status == "blocked":
            raise ValueError("blocked run cannot be packaged")
        if run.status not in {"completed", "review_required"}:
            raise ValueError(f"run status {run.status!r} is not packageable")
        if not run.manifest_path:
            raise ValueError("run manifest is missing")
        manifest_path = Path(run.manifest_path).expanduser().resolve()
        try:
            manifest_path.relative_to(self.workspace.derived_root.resolve())
        except ValueError as exc:
            raise ValueError("run manifest must be inside .polynexus") from exc
        if not manifest_path.is_file():
            raise ValueError("run manifest is missing")
        import json
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("run manifest is invalid") from exc
        if not isinstance(manifest, dict):
            raise ValueError("run manifest is invalid")
        for key, expected in (("run_id", run.run_id), ("request_hash", run.request_hash), ("plan_hash", run.plan_hash), ("recipe_hash", run.recipe_hash), ("status", run.status)):
            if manifest.get(key) != expected:
                raise ValueError("run manifest does not match run")
        manifest_items = manifest.get("evidence_items", ())
        if not isinstance(manifest_items, list):
            raise ValueError("run manifest evidence is invalid")
        expected_hashes = {item.item_hash for item in run.evidence_items}
        actual_hashes = set()
        for value in manifest_items:
            try:
                actual_hashes.add(EvidenceItem.from_dict(value).item_hash)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("run manifest evidence is invalid") from exc
        if actual_hashes != expected_hashes:
            raise ValueError("run manifest evidence does not match run")
        analysis_payload = manifest.get("analysis_run")
        if not isinstance(analysis_payload, Mapping):
            raise ValueError("run manifest analysis record is missing")
        try:
            analysis_run = AnalysisRun.from_dict(analysis_payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("run manifest analysis record is invalid") from exc
        if analysis_run.recipe.recipe_hash != run.recipe_hash or not analysis_run.validated:
            raise ValueError("run manifest analysis record does not match run")
        if run.analysis_run is not None and analysis_run.to_dict() != run.analysis_run.to_dict():
            raise ValueError("run manifest analysis record does not match run")
        source_hashes = sorted(str(value) for value in manifest.get("source_hashes", ()))
        recipe_hashes = sorted(str(item.sha256) for item in analysis_run.recipe.artifacts if item.sha256)
        if source_hashes != recipe_hashes:
            raise ValueError("run manifest source hashes do not match recipe")
        for artifact in analysis_run.recipe.artifacts:
            if not artifact.sha256:
                raise ValueError("run manifest source hash is missing")
            source = Path(artifact.path).expanduser()
            if source.is_file():
                current_hash = _sha256_file(source)
            elif source.is_dir():
                current_hash = _sha256_directory(source)
            else:
                current_hash = None
            if current_hash != artifact.sha256:
                raise ValueError("run manifest source hash no longer matches")
        return manifest

    def _next_version(self, package_id: str) -> int:
        versions = []
        if self.workspace.evidence_dir.exists():
            for child in self.workspace.evidence_dir.iterdir():
                if not child.is_dir():
                    continue
                match = _VERSION_RE.match(child.name)
                if match and match.group("name") == package_id:
                    try:
                        versions.append(int(match.group("version")))
                    except ValueError:
                        pass
        return max(versions, default=0) + 1

    def _asset_descriptors(
        self, run: ProjectWorkflowRun, package_id: str, *, include_figures: bool = True
    ) -> list[dict[str, Any]]:
        assets: list[dict[str, Any]] = []
        techniques = {
            str(item.technique).upper()
            for item in run.evidence_items
            if str(item.technique).strip()
        }
        technique = next(iter(techniques)) if len(techniques) == 1 else "UNKNOWN"
        for output in run.outputs:
            source = Path(output).expanduser().resolve()
            if not source.is_file() or source.name.endswith(".json") and source.name == f"{run.run_id}.json":
                continue
            try:
                relative = source.relative_to(self.workspace.derived_root.resolve())
            except ValueError:
                continue
            lower_parts = {part.lower() for part in relative.parts}
            suffix = source.suffix.lower()
            if suffix in _FIGURE_SUFFIXES or "figures" in lower_parts or "figure" in source.stem.lower():
                if not include_figures:
                    continue
                kind = "figures"
            elif suffix in _TABLE_SUFFIXES or "tables" in lower_parts or "table" in source.stem.lower():
                kind = "tables"
            else:
                continue
            assets.append({
                "source": str(source),
                "kind": kind,
                "name": source.name,
                "role": "diagnostic",
                "technique": technique,
                "group": None,
                "writing_eligibility": "review_only",
            })
        return assets

    def _candidate_asset_descriptors(self, candidates: FigureCandidateSet) -> list[dict[str, Any]]:
        """Return only main/supporting candidate assets from project-local figures."""
        assets: list[dict[str, Any]] = []
        metadata_by_logical_figure: dict[str, tuple[str, str, tuple[str, ...]]] = {}
        figures_root = self.workspace.figures_dir.resolve()
        for candidate_role, values in (
            ("manuscript_candidate", candidates.main_candidates),
            ("supporting_candidate", candidates.supporting_candidates),
        ):
            for candidate in values:
                candidate_paths = tuple(Path(value).expanduser().resolve() for value in candidate.paths)
                if not any(path.suffix.lower() == ".svg" for path in candidate_paths):
                    raise ValueError("figure candidate svg is missing")
                group = candidate.group_ids[0] if len(candidate.group_ids) == 1 else None
                for source in candidate_paths:
                    try:
                        source.relative_to(figures_root)
                    except ValueError as exc:
                        raise ValueError("figure candidate asset must be inside .polynexus/figures") from exc
                    if not source.is_file() or source.suffix.lower() not in _FIGURE_SUFFIXES:
                        raise ValueError("figure candidate asset is invalid")
                    logical_figure_key = self._candidate_logical_figure_key(source)
                    metadata = (
                        candidate_role,
                        str(candidate.technique).upper(),
                        tuple(str(value) for value in candidate.group_ids),
                    )
                    existing_metadata = metadata_by_logical_figure.get(logical_figure_key)
                    if existing_metadata is not None and existing_metadata != metadata:
                        if existing_metadata[0] != candidate_role:
                            raise ValueError("conflicting figure candidate role")
                        raise ValueError("conflicting figure candidate metadata")
                    metadata_by_logical_figure[logical_figure_key] = metadata
                    assets.append({
                        "source": str(source),
                        "kind": "figures",
                        "name": source.name,
                        "role": candidate_role,
                        "technique": str(candidate.technique).upper(),
                        "group": group,
                        "writing_eligibility": "review_only",
                        "logical_figure_key": logical_figure_key,
                    })
        return assets

    @staticmethod
    def _candidate_logical_figure_key(source: Path) -> str:
        """Normalize the renderer's conventional ``preview`` sibling name."""
        stem = source.stem.lower()
        logical_stem = "figure" if stem in {"preview", "thumbnail"} else source.stem
        return str(source.parent / logical_stem)

    @staticmethod
    def _package_figure_candidate_payload(
        payload: Mapping[str, Any], assets: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Point packaged candidate metadata at the copied package assets."""
        by_source = {str(item["source"]): f"{item['kind']}/{item['name']}" for item in assets}
        result = dict(payload)
        for key in ("main_candidates", "supporting_candidates"):
            candidates = []
            for value in payload.get(key, ()):
                candidate = dict(value)
                candidate["paths"] = [
                    by_source[str(path)]
                    for path in candidate.get("paths", ())
                    if str(path) in by_source
                ]
                candidates.append(candidate)
            result[key] = candidates
        manifest_path = result.get("manifest_path")
        if manifest_path:
            result["manifest_path"] = "figure-candidates.json"
        return result

    @staticmethod
    def _asset_hashes(assets: list[dict[str, str]]) -> list[dict[str, str]]:
        values: list[dict[str, str]] = []
        destinations: set[tuple[str, str]] = set()
        for asset in assets:
            destination = (asset["kind"], asset["name"])
            if destination in destinations:
                raise ValueError("package asset destination collides")
            destinations.add(destination)
            values.append({
                "kind": asset["kind"],
                "name": asset["name"],
                "sha256": _sha256_file(Path(asset["source"])),
            })
        return values

    @staticmethod
    def _package_artifact_hashes(package_path: Path) -> list[dict[str, str]]:
        return [
            {
                "path": path.relative_to(package_path).as_posix(),
                "sha256": _sha256_file(path),
            }
            for path in sorted(package_path.rglob("*"))
            if path.is_file() and path.relative_to(package_path).as_posix() != "manifest.json"
        ]

    @staticmethod
    def _disambiguate_assets(assets: list[dict[str, str]]) -> list[dict[str, str]]:
        """Give same-named derived assets stable names instead of overwriting."""
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
        for asset in assets:
            grouped.setdefault((asset["kind"], asset["name"]), []).append(asset)
        result: list[dict[str, str]] = []
        for (_, original_name), values in grouped.items():
            sources = {value["source"] for value in values}
            if len(sources) == 1:
                result.append(dict(values[0]))
                continue
            for value in values:
                source = Path(value["source"])
                digest = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:10]
                updated = dict(value)
                updated["name"] = f"{source.stem}-{digest}{source.suffix}"
                result.append(updated)
        return result

    @staticmethod
    def _copy_assets(assets: list[dict[str, str]], package_path: Path) -> None:
        for asset in assets:
            destination = package_path / asset["kind"] / asset["name"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset["source"], destination)

    @staticmethod
    def _writing_input(
        manifest: Mapping[str, Any],
        evidence: list[Mapping[str, Any]],
        limitations: list[str],
        writing_evidence: Mapping[str, Any] | None = None,
    ) -> str:
        lines = [
            "# Research evidence package",
            "",
            f"Package: {manifest['package_id']}-v{int(manifest['version']):03d}",
            f"Status: {manifest['status']}",
            f"Runs: {', '.join(manifest['run_ids'])}",
            "",
            "## Evidence",
        ]
        for item in evidence:
            lines.append(f"- [{item.get('status', 'unknown')}] {item.get('technique', 'unknown')}: {item.get('claim_scope', '')}")
            for interpretation in item.get("supported_interpretations", ()):
                lines.append(f"  Supported: {interpretation}")
            for conclusion in item.get("disallowed_conclusions", ()):
                lines.append(f"  Do not conclude: {conclusion}")
        lines.extend(("", "## Limitations"))
        lines.extend(f"- {value}" for value in limitations)
        if isinstance(writing_evidence, Mapping):
            lines.extend(("", "Citation metrics: citation-metrics.json", "", "## Writing evidence by technique"))
            for technique, group in writing_evidence.get("techniques", {}).items():
                lines.extend((f"### {str(technique).upper()}", f"- Status: {', '.join(group.get('statuses', ())) }"))
                for item in group.get("evidence", ()):
                    lines.append(f"- Evidence: {item.get('claim_scope', '')}")
                    counts = item.get("citation_metric_counts", {})
                    if isinstance(counts, Mapping) and counts:
                        lines.append(
                            "  Citation metrics: "
                            + ", ".join(f"{key}={value}" for key, value in counts.items())
                        )
                    for figure in item.get("figures", ()):
                        lines.append(f"  Figure: {figure}")
                    for supported in item.get("supported_interpretations", ()):
                        lines.append(f"  Supported: {supported}")
                    for blocked in item.get("disallowed_conclusions", ()):
                        lines.append(f"  Do not conclude: {blocked}")
        candidates = manifest.get("figure_candidates")
        if isinstance(candidates, Mapping):
            lines.extend(("", "## Manuscript figure candidates"))
            for candidate in candidates.get("main_candidates", ()):
                if isinstance(candidate, Mapping):
                    lines.append(
                        f"- {candidate.get('kind', 'figure')}: "
                        f"{', '.join(str(path) for path in candidate.get('paths', ())) }"
                    )
            for reason in candidates.get("omission_reasons", ()):
                lines.append(f"- Omitted: {reason}")
        parameters = manifest.get("request_parameters", {})
        corrections = parameters.get("approved_context_corrections") if isinstance(parameters, Mapping) else None
        if isinstance(corrections, Mapping) and corrections:
            lines.extend(("", "## Approved context corrections", "- User-approved request metadata; not raw instrument facts."))
            lines.extend(f"- {key}: {value}" for key, value in corrections.items())
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
        try:
            with handle:
                handle.write(canonical_json(payload))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(handle.name).replace(path)
        finally:
            temporary = Path(handle.name)
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
        try:
            with handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            Path(handle.name).replace(path)
        finally:
            temporary = Path(handle.name)
            if temporary.exists():
                temporary.unlink()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_directory(path: Path) -> str:
    """Hash a directory by sorted relative file names and file digests."""
    entries: list[dict[str, str]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        if candidate.is_symlink():
            raise ValueError("directory source contains symlink")
        if not candidate.is_file():
            continue
        entries.append({
            "path": candidate.relative_to(path).as_posix(),
            "sha256": _sha256_file(candidate),
        })
    if not entries:
        return ""
    return hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


__all__ = ["ProjectEvidencePackager", "ResearchEvidencePackage"]
