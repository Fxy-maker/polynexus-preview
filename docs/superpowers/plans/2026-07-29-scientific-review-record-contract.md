# Scientific Review Record Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a technique-neutral, immutable scientific review record that is JSON-safe, source-aware, and fail-closed before later IR/NMR/Joint promotion work.

**Architecture:** Add the record to `polynexus/core/scientific_review.py` as a small core contract. It will validate scope/status/required decision keys, serialize detached JSON-safe payloads, and expose a pure promotion gate. Existing engines and GUI surfaces will consume the payload in later value-specific tasks; this slice does not change any scientific result or publication role.

**Tech Stack:** Python dataclasses, `json`, pytest, existing `scripts/verify.py` and `scripts/auto_commit.py`.

---

### Task 1: Lock the review record contract with RED tests

**Files:**
- Create: `tests/test_scientific_review.py`
- Read: `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`

- [ ] **Step 1: Write the failing tests**

Add tests for the public contract below:

```python
def accepted_ir_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-ir-1",
        scope="ir.mapping",
        reviewer="reviewer-a",
        reviewed_at="2026-07-29",
        policy_version="ir-map-v1",
        source_refs=("map-a.json",),
        decisions={
            "coordinate_convention": "row/column supplied by vendor",
            "roi_inclusion_policy": "explicit mask",
            "invalid_pixel_policy": "masked",
            "promotion_rule": "reviewed source",
        },
        status="accepted",
    )


def test_pending_record_is_json_safe_but_not_promotable():
    record = ScientificReviewRecord.pending(
        record_id="review-ir-1",
        scope="ir.mapping",
        source_refs=("map-a.json",),
    )
    assert json.loads(record.to_json())["status"] == "pending"
    assert promotion_decision(record, expected_scope="ir.mapping", source_ref="map-a.json").allowed is False


def test_accepted_record_requires_scope_fields_reviewer_and_source():
    record = accepted_ir_record()
    assert validate_review_record(record) == record
    assert promotion_decision(record, expected_scope="ir.mapping", source_ref="map-a.json").allowed is True


def test_promotion_is_denied_for_scope_source_or_status_mismatch():
    record = accepted_ir_record()
    assert promotion_decision(record, expected_scope="joint", source_ref="map-a.json").allowed is False
    assert promotion_decision(record, expected_scope="ir.mapping", source_ref="other.json").allowed is False
    rejected = replace(record, status="conditional")
    assert promotion_decision(rejected, expected_scope="ir.mapping", source_ref="map-a.json").allowed is False


def test_non_finite_decision_values_fail_json_validation():
    record = replace(accepted_ir_record(), decisions={"coordinate_convention": float("nan")})
    with pytest.raises(ValueError, match="JSON-safe"):
        record.to_json()
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py
```

Expected result: collection fails because `polynexus.core.scientific_review` and its public record/gate functions do not exist yet.

### Task 2: Implement the immutable JSON-safe record and gate

**Files:**
- Create: `polynexus/core/scientific_review.py`
- Modify: `polynexus/core/__init__.py`
- Test: `tests/test_scientific_review.py`

- [ ] **Step 1: Add the immutable record**

Implement `ScientificReviewRecord` with these exact public fields:

```python
@dataclass(frozen=True)
class ScientificReviewRecord:
    record_id: str
    scope: str
    reviewer: str = ""
    reviewed_at: str = ""
    policy_version: str = ""
    source_refs: tuple[str, ...] = ()
    decisions: Mapping[str, Any] = field(default_factory=dict)
    status: str = "pending"
    conditions: tuple[str, ...] = ()
```

Support `pending(record_id: str, scope: str, source_refs: tuple[str, ...] = ())`,
`to_dict()`, and `to_json()` helpers. The serializer must detach
mappings/sequences and use `allow_nan=False`; non-finite floats must raise
`ValueError` rather than be silently converted.

- [ ] **Step 2: Add scope validation and the pure gate**

Define these constants and functions:

```python
REVIEW_SCOPES = frozenset({"ir.mapping", "nmr.solid_c", "joint", "release"})
REVIEW_STATUSES = frozenset({"pending", "accepted", "conditional", "rejected", "stale"})

def validate_review_record(record: ScientificReviewRecord) -> ScientificReviewRecord:
    """Validate and return one immutable review record."""


def promotion_decision(
    record: ScientificReviewRecord | None,
    *,
    expected_scope: str,
    source_ref: str = "",
) -> ReviewPromotionDecision:
    """Return the immutable, fail-closed promotion decision for one source."""
```

`validate_review_record` must reject unknown scopes/statuses, empty IDs, malformed source references, non-mapping decisions, and missing required keys for a non-pending record. `promotion_decision` must return `allowed=False` with a stable reason for absent, pending, rejected, stale, conditional, wrong-scope, or source-mismatched records. Only `accepted` with matching scope/source and complete required keys may return `allowed=True`.

- [ ] **Step 3: Export the public contract and run GREEN**

Export the record, gate result, constants, and validators from `polynexus.core`. Run:

```powershell
python -m pytest -q tests/test_scientific_review.py
```

Expected result: all focused tests pass and `json.dumps(record.to_dict(), allow_nan=False)` succeeds for valid records.

### Task 3: Verify the shared-only boundary and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-scientific-review-record-contract.md`
- Modify: `docs/acceptance/2026-07-29-scientific-review-record-contract.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run focused and structured verification**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-record-contract.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

Expected result: focused tests pass, the structured verifier exits `0`, boundary audit exits `0`, and diff check is clean. No full release or scientific approval is claimed by this slice.

- [ ] **Step 2: Create the atomic checkpoint**

Run only after the commands above pass:

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add scientific review record contract" `
  --files polynexus/core/scientific_review.py polynexus/core/__init__.py `
  tests/test_scientific_review.py `
  docs/agent/tasks/2026-07-29-scientific-review-record-contract.md `
  docs/acceptance/2026-07-29-scientific-review-record-contract.md `
  docs/agent/memory/active-work.md
```

The commit must contain only the explicit allowlist. It must not include current SAXS edits, `current-state.md`, or untracked test-storage directories.

## Follow-up boundary

After this shared contract is checkpointed, the reviewer must supply concrete
values. Create separate implementation tasks for IR mapping, NMR solid-C, Joint
conflict policy, and final release promotion; do not make this shared contract
implicitly decide any of those scientific values.
