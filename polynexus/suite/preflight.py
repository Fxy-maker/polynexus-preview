"""Deterministic structural checks for manuscript source projections.

The legacy :func:`preflight_manuscript` function remains intentionally
advisory for internal drafts.  :func:`submission_preflight` adds the stricter
publication boundary used by the Codex--ARS research loop.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .paper_contracts import PreflightReport


def preflight_manuscript(manuscript: Mapping[str, Any]) -> PreflightReport:
    errors: list[str] = []
    warnings: list[str] = []
    source_id = str(manuscript.get("source_id", ""))
    if not source_id:
        errors.append("source_id_missing")
    claims = manuscript.get("claims", [])
    figures = manuscript.get("figures", [])
    citations = manuscript.get("citations", [])
    citation_keys = {str(c.get("key")) for c in citations if isinstance(c, Mapping)}
    formula_ids = {str(f.get("formula_id")) for f in manuscript.get("formulas", []) if isinstance(f, Mapping)}
    claim_ids = {str(c.get("claim_id")) for c in claims if isinstance(c, Mapping)}
    for section in manuscript.get("sections", []):
        if isinstance(section, Mapping):
            for claim_id in section.get("claim_ids", []):
                if str(claim_id) not in claim_ids:
                    errors.append(f"claim_unbound:{claim_id}")
    if not figures:
        warnings.append("no_figures")
    if not citations:
        warnings.append("no_citations")
    for claim in claims:
        if isinstance(claim, Mapping) and not (claim.get("evidence_ids") or claim.get("metric_ids")):
            errors.append(f"claim_without_evidence:{claim.get('claim_id', '')}")
        if isinstance(claim, Mapping):
            for key in claim.get("citation_keys", ()):
                if str(key) not in citation_keys:
                    errors.append(f"citation_unbound:{key}")
    checks = {"claims": "passed" if not errors else "failed", "figures": "passed" if figures else "review_required", "citations": "passed" if citations else "review_required", "formulas": "passed" if formula_ids or not manuscript.get("formulas") else "failed"}
    return PreflightReport.create(source_id=source_id or "unknown", errors=tuple(dict.fromkeys(errors)), warnings=tuple(dict.fromkeys(warnings)), checks=checks)


_PASS_STATES = frozenset({"passed", "pass", "complete", "completed", "verified", "ready", "finalized"})
_ARS_COMPLETE_STATES = frozenset(
    {"passed", "pass", "complete", "completed", "verified", "finalized"}
)
_INTERNAL_TERM_PATTERNS = (
    re.compile(r"\bevidence[ _-]*package\b", re.IGNORECASE),
    re.compile(r"证据包"),
    re.compile(r"\breview_required\b", re.IGNORECASE),
    re.compile(r"\bhuman_review_required\b", re.IGNORECASE),
    re.compile(r"\b(?:package|run|evidence)_id\b", re.IGNORECASE),
    re.compile(r"\bsha[-_ ]?256\b", re.IGNORECASE),
    re.compile(r"\bhash\s*=", re.IGNORECASE),
    re.compile(r"\bsource\s*=", re.IGNORECASE),
    re.compile(r"\bdiagnostic_only\b", re.IGNORECASE),
)


def _state(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("status", "state", "verdict", "result"):
            if key in value:
                return str(value.get(key, "")).strip().lower()
        return ""
    if isinstance(value, bool):
        return "passed" if value else "failed"
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_passed(value: Any) -> bool:
    return _state(value) in _PASS_STATES


def _visible_text(manuscript: Mapping[str, Any], explicit: Any = None) -> str:
    values: list[str] = []

    def append_visible(value: Any) -> None:
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, Mapping):
            for item in value.values():
                append_visible(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                append_visible(item)

    for key in ("title", "abstract", "keywords", "visible_text"):
        value = manuscript.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, Mapping):
            values.extend(str(item) for item in value.values() if isinstance(item, (str, int, float)))
        elif isinstance(value, (list, tuple)):
            values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
    # These are common renderer-facing containers rather than provenance
    # fields.  Traverse their nested strings so a clean top-level
    # ``visible_text`` projection cannot hide internal audit language in the
    # actual body, Results, or Discussion content.
    for key in (
        "body",
        "introduction",
        "results",
        "discussion",
        "methods_text",
        "conclusion",
        "full_text",
        "manuscript_text",
    ):
        if key in manuscript:
            append_visible(manuscript[key])
    for section in manuscript.get("sections", ()):
        if isinstance(section, Mapping):
            for key in ("title", "name", "content", "text", "body"):
                if key in section:
                    append_visible(section[key])
    for claim in manuscript.get("claims", ()):
        if isinstance(claim, Mapping) and isinstance(claim.get("text"), str):
            values.append(str(claim["text"]))
    # Explicit projections are additive.  They may identify text emitted by a
    # renderer, but must never hide internal audit terms already present in the
    # manuscript source itself.
    if explicit is not None:
        values.append(str(explicit))
    return "\n".join(values)


def _method_gate(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        if "complete" in value and value.get("complete") is not True:
            return False
        missing = value.get("missing", value.get("missing_fields", ()))
        if isinstance(missing, (list, tuple, set, frozenset)) and missing:
            return False
        if "status" in value or "state" in value:
            return _is_passed(value)
        return value.get("complete") is True
    return _is_passed(value)


def _citation_gate(value: Any) -> tuple[bool, bool]:
    """Return ``(present, verified)`` for citation records."""
    if value is None:
        return False, False
    if isinstance(value, Mapping):
        records = value.get("records", value.get("items", value.get("citations")))
        if records is None:
            return True, _is_passed(value)
        value = records
    if not isinstance(value, (list, tuple)):
        return False, False
    if not value:
        return False, False
    verified = True
    for item in value:
        if not isinstance(item, Mapping):
            verified = False
            continue
        has_verification = False
        if "verified" in item:
            has_verification = True
            if type(item.get("verified")) is not bool or item.get("verified") is not True:
                verified = False
        if "verification_status" in item:
            has_verification = True
            status = item.get("verification_status")
            if not isinstance(status, str) or not _is_passed(status):
                verified = False
        if "status" in item:
            has_verification = True
            status = item.get("status")
            if not isinstance(status, str) or not _is_passed(status):
                verified = False
        if not has_verification:
            verified = False
    return True, verified


def _citation_records(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        records = value.get("records", value.get("items", value.get("citations")))
        if records is None:
            return ()
        value = records
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _citation_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    for item in _citation_records(value):
        for field in ("key", "citation_key", "citation_id", "id"):
            text = str(item.get(field, "")).strip()
            if text:
                keys.add(text)
                break
    return keys


def _citation_explicitly_failed(value: Any) -> bool:
    """Return true for a negative record that no outside gate may override."""
    for item in _citation_records(value):
        if "verified" in item:
            verified = item.get("verified")
            if type(verified) is not bool or verified is not True:
                return True
        for field in ("verification_status", "status"):
            if field in item:
                status = item.get(field)
                if not isinstance(status, str) or not _is_passed(status):
                    return True
    return False


def _zotero_gate(value: Any) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, Mapping):
        for field in ("connected", "available", "verified"):
            if field in value and (
                type(value.get(field)) is not bool or value.get(field) is not True
            ):
                return False
        if "status" in value or "state" in value:
            state = value.get("status", value.get("state"))
            return isinstance(state, str) and _is_passed(state)
        return type(value.get("verified")) is bool and value.get("verified") is True
    return isinstance(value, str) and _is_passed(value)


def _ars_gate(value: Any) -> bool:
    if isinstance(value, Mapping):
        state = value.get("status", value.get("state", value.get("verdict")))
    else:
        state = value
    if not isinstance(state, str) or state.strip().lower() not in _ARS_COMPLETE_STATES:
        return False
    if isinstance(value, Mapping) and "integrity" in value:
        integrity = value["integrity"]
        return (
            isinstance(integrity, str)
            and integrity.strip().lower() in _ARS_COMPLETE_STATES
        )
    return True


def _format_gate(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not isinstance(value, Mapping):
        return _is_passed(value)
    if value.get("passed") is False or value.get("valid") is False:
        return False
    errors = value.get("errors", ())
    if isinstance(errors, (list, tuple, set, frozenset)) and errors:
        return False
    return _is_passed(value) or value.get("passed") is True or value.get("valid") is True


def _review_pending(value: Any) -> bool:
    if value is None:
        return False
    values: Iterable[Any]
    if isinstance(value, Mapping):
        # Gate projections are commonly emitted as a single object
        # (``{"status": "pending"}``) rather than a decisions list.  Read
        # the top-level state first, then inspect any nested decisions/items.
        state_keys = tuple(key for key in ("status", "state", "verdict") if key in value)
        if any(not _review_state_resolved(value.get(key)) for key in state_keys):
            return True
        values = value.get("decisions", value.get("items", ()))
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        return not _is_passed(value)
    for item in values:
        if not isinstance(item, Mapping):
            return True
        state = _state(item.get("decision", item.get("status", item.get("state", item.get("verdict", "pending")))))
        if not _review_state_resolved(state):
            return True
    return False


_REVIEW_RESOLVED_STATES = frozenset({"resolved", "approved", "accepted", "not_required"})


def _review_state_resolved(value: Any) -> bool:
    state = _state(value)
    return state in _PASS_STATES or state in _REVIEW_RESOLVED_STATES


def _reference_ids(manuscript: Mapping[str, Any]) -> dict[str, set[str]]:
    """Collect IDs that are actually present in the manuscript projection.

    Claims are only allowed to cite objects carried by the manuscript itself:
    top-level evidence/metric/figure/section collections or the source/evidence
    projection.  This intentionally does not treat an arbitrary claim string as
    evidence and therefore rejects forged identifiers.
    """
    found: dict[str, set[str]] = {"evidence": set(), "metric": set(), "figure": set(), "section": set()}

    def add(category: str | None, value: Any) -> None:
        if category not in found:
            return
        if value is None or isinstance(value, (Mapping, list, tuple, set, frozenset)):
            return
        text = str(value).strip()
        if text:
            found[category].add(text)

    identity_fields = {
        "evidence": ("evidence_id", "id"),
        "metric": ("metric_id", "id"),
        "figure": ("figure_id", "id"),
        "section": ("section_id", "id"),
    }
    container_fields = frozenset({"items", "records", "values", "data", "manifest"})

    def walk(value: Any, category: str | None = None) -> None:
        if isinstance(value, Mapping):
            found_identity = False
            if category in found:
                for field in identity_fields[category]:
                    if field in value:
                        add(category, value.get(field))
                        found_identity = True
                if category == "section":
                    for field in ("name", "title"):
                        if field in value:
                            add(category, value.get(field))
            for key, child in value.items():
                key_text = str(key).lower()
                child_category = _category_for_key(key_text)
                if child_category is not None:
                    walk(child, child_category)
                elif category in found and key_text in container_fields:
                    walk(child, category)
            # Support a collection encoded as {"metric-1": {...}} without
            # treating arbitrary nested provenance fields such as ``run_id``
            # as identifiers for the surrounding category.
            if (
                category in found
                and not found_identity
                and value
                and all(isinstance(child, Mapping) for child in value.values())
            ):
                for key, child in value.items():
                    add(category, key)
                    walk(child, category)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                walk(item, category)

    for key in ("evidence", "evidences", "metrics", "figures", "sections", "sources", "source_projection", "evidence_projection"):
        if key in manuscript:
            walk(manuscript[key], _category_for_key(key))
    return found


def _category_for_key(key: str) -> str | None:
    text = str(key).lower()
    if text in {"evidence", "evidences", "evidence_id"}:
        return "evidence"
    if text in {"metric", "metrics", "metric_id"}:
        return "metric"
    if text == "metric_manifest":
        return "metric"
    if text in {"figure", "figures", "figure_id"}:
        return "figure"
    if text in {"section", "sections", "section_id"}:
        return "section"
    return None


def submission_preflight(
    manuscript: Mapping[str, Any],
    *,
    ars_state: Any = None,
    methods: Any = None,
    citations: Any = None,
    zotero: Any = None,
    format_report: Any = None,
    human_review: Any = None,
    visible_text: Any = None,
) -> PreflightReport:
    """Run the non-bypassable formal manuscript submission gates.

    The function accepts explicit gate projections, while falling back to
    same-named fields on ``manuscript`` for JSON handoffs.  It never changes
    scientific values and intentionally leaves the legacy structural
    ``preflight_manuscript`` contract untouched.
    """
    if not isinstance(manuscript, Mapping):
        raise ValueError("manuscript is invalid")
    base = preflight_manuscript(manuscript)
    errors = list(base.errors)
    warnings = list(base.warnings)
    checks = dict(base.checks)

    ars_value = manuscript.get("ars_workflow", manuscript.get("ars_state")) if ars_state is None else ars_state
    if not _ars_gate(ars_value):
        errors.append("ars_workflow_incomplete")
        checks["ars"] = "failed"
    else:
        checks["ars"] = "passed"

    methods_value = manuscript.get("methods") if methods is None else methods
    if not _method_gate(methods_value):
        errors.append("methods_incomplete")
        checks["methods"] = "failed"
    else:
        checks["methods"] = "passed"

    manuscript_citations = manuscript.get("citations")
    citation_present, manuscript_citations_verified = _citation_gate(manuscript_citations)
    if citations is None:
        citation_verified = manuscript_citations_verified
    else:
        external_present, external_verified = _citation_gate(citations)
        manuscript_keys = _citation_keys(manuscript_citations)
        external_keys = _citation_keys(citations)
        citation_verified = (
            citation_present
            and external_present
            and external_verified
            and bool(manuscript_keys)
            and manuscript_keys.issubset(external_keys)
            and not _citation_explicitly_failed(manuscript_citations)
        )
    if not citation_present:
        errors.append("citations_missing")
        checks["citations"] = "failed"
    elif not citation_verified:
        errors.append("citations_unverified")
        checks["citations"] = "failed"
    else:
        checks["citations"] = "passed"

    zotero_value = manuscript.get("zotero") if zotero is None else zotero
    if not _zotero_gate(zotero_value):
        errors.append("zotero_unverified")
        checks["zotero"] = "failed"
    else:
        checks["zotero"] = "passed"

    format_value = manuscript.get("format_report") if format_report is None else format_report
    if not _format_gate(format_value):
        errors.append("format_invalid")
        checks["format"] = "failed"
    else:
        checks["format"] = "passed"

    review_value = manuscript.get("human_review") if human_review is None else human_review
    if _review_pending(review_value):
        errors.append("human_review_pending")
        checks["human_review"] = "failed"
    else:
        checks["human_review"] = "passed"

    text = _visible_text(manuscript, visible_text)
    if not text.strip():
        errors.append("visible_text_missing")
        checks["visible_text"] = "failed"
    else:
        leaked = any(pattern.search(text) for pattern in _INTERNAL_TERM_PATTERNS)
        if leaked:
            errors.append("internal_term_leak")
            checks["visible_text"] = "failed"
        else:
            checks["visible_text"] = "passed"

    # A claim must point to at least one source object and every section claim
    # reference must resolve.  The legacy preflight catches part of this, but
    # this explicit check makes the formal gate stable for sparse projections.
    claims = manuscript.get("claims", ())
    traceability_failed = False
    references = _reference_ids(manuscript)
    if not isinstance(claims, (list, tuple)):
        traceability_failed = True
    else:
        for claim in claims:
            if not isinstance(claim, Mapping):
                traceability_failed = True
                errors.append("claim_source_unbound")
                continue
            refs = {
                "evidence": claim.get("evidence_ids", ()),
                "metric": claim.get("metric_ids", ()),
                "figure": claim.get("figure_ids", ()),
                "section": claim.get("section_ids", ()),
            }
            if not any(refs.values()):
                traceability_failed = True
                errors.append(f"claim_source_unbound:{claim.get('claim_id', '')}")
                continue
            for category, values in refs.items():
                if isinstance(values, (str, bytes)):
                    values = (values,)
                if not isinstance(values, (list, tuple, set, frozenset)):
                    traceability_failed = True
                    errors.append(f"{category}_unbound:{values}")
                    continue
                for value in values:
                    identifier = str(value)
                    if identifier not in references[category]:
                        traceability_failed = True
                        errors.append(f"{category}_unbound:{identifier}")
    checks["traceability"] = "failed" if traceability_failed else "passed"

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    checks["submission"] = "failed" if errors else ("review_required" if warnings else "passed")
    return PreflightReport.create(
        source_id=str(manuscript.get("source_id", "")) or "unknown",
        errors=tuple(errors),
        warnings=tuple(warnings),
        checks=checks,
    )


__all__ = ["preflight_manuscript", "submission_preflight"]
