# PolyNexus Suite Runtime and Skill Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared Suite Manager that discovers Codex/ARS, installs pinned skills safely, rolls back failed updates, and creates a validated evidence-package handoff.

**Architecture:** A technique-neutral `polynexus.suite` service owns manifest, lock, compatibility, staging, and handoff DTOs. CLI commands delegate to that service; GUI receives the same JSON-safe projections through a thin adapter. Existing Core and project/evidence contracts remain producers of scientific values.

**Tech Stack:** Python 3.10+, dataclasses, pathlib, hashlib, json, argparse, pytest.

---

### Task 1: Add Suite contracts and manifest/lock persistence

**Files:**
- Create: `polynexus/suite/__init__.py`
- Create: `polynexus/suite/contracts.py`
- Create: `polynexus/suite/manifest.py`
- Create: `tests/test_suite_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from polynexus.suite.contracts import SuiteComponent, SuiteStatus
from polynexus.suite.manifest import load_manifest, load_lock, write_lock


def test_manifest_loads_pinned_component_and_lock_round_trips(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        '{"schema_version":1,"components":[{"id":"ars","version":"0.1.18",'
        '"destination":"academic-research-suite","required_files":["SKILL.md"],'
        '"source":"file:///fixture","sha256":"abc","core_range":"1.x",'
        '"handoff_schema":"v1"}]}', encoding="utf-8"
    )
    manifest = load_manifest(manifest_path)
    assert manifest.components[0] == SuiteComponent(
        component_id="ars", version="0.1.18", destination="academic-research-suite",
        required_files=("SKILL.md",), source="file:///fixture", sha256="abc",
        core_range="1.x", handoff_schema="v1"
    )
    lock_path = tmp_path / "suite-lock.json"
    write_lock(lock_path, {"core_version":"1.0.0", "components":{"ars":"0.1.18"}})
    assert load_lock(lock_path)["components"]["ars"] == "0.1.18"


def test_invalid_manifest_is_rejected(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version":1,"components":[]}', encoding="utf-8")
    try:
        load_manifest(path)
    except ValueError as exc:
        assert "component" in str(exc)
    else:
        raise AssertionError("invalid manifest accepted")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_contracts.py`

Expected: FAIL because `polynexus.suite` does not exist.

- [ ] **Step 3: Implement the contracts and persistence**

Implement frozen dataclasses `SuiteComponent`, `SuiteManifest`, and `SuiteStatus` with JSON-safe `to_dict()` methods. `load_manifest()` must require schema version `1`, at least one component, non-empty ids/versions/destinations, and relative required-file paths. `write_lock()` must create the parent directory and atomically replace a UTF-8 JSON file through a sibling temporary file. `load_lock()` returns `{}` for a missing lock and rejects non-object JSON.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_contracts.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
python scripts/auto_commit.py --message "feat(suite): add manifest and lock contracts" --files polynexus/suite/__init__.py polynexus/suite/contracts.py polynexus/suite/manifest.py tests/test_suite_contracts.py
```

### Task 2: Implement discovery, integrity validation, compatibility, and rollback

**Files:**
- Create: `polynexus/suite/manager.py`
- Create: `tests/test_suite_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
import hashlib
import json
from pathlib import Path

from polynexus.suite.manager import SuiteManager


def _manifest(path: Path, source: Path) -> Path:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    payload = {"schema_version":1,"components":[{"id":"ars","version":"0.1.18",
        "destination":"academic-research-suite","required_files":["SKILL.md"],
        "source":str(source),"sha256":digest,"core_range":"1.x","handoff_schema":"v1"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_install_validates_and_doctor_reports_installed(tmp_path: Path):
    source = tmp_path / "ars.zip"
    source.write_bytes(b"fixture")
    manifest = _manifest(tmp_path / "manifest.json", source)
    codex = tmp_path / "codex" / "skills"
    manager = SuiteManager(manifest_path=manifest, codex_skills_dir=codex, core_version="1.0.0", lock_path=tmp_path / "lock.json")
    result = manager.install("ars", confirm=True)
    assert result.status == "installed"
    assert (codex / "academic-research-suite" / "SKILL.md").is_file()
    assert manager.doctor().components[0].status == "installed"


def test_failed_activation_restores_previous_installation(tmp_path: Path, monkeypatch):
    source = tmp_path / "ars.zip"
    source.write_bytes(b"fixture")
    manifest = _manifest(tmp_path / "manifest.json", source)
    codex = tmp_path / "codex" / "skills"
    target = codex / "academic-research-suite"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("old", encoding="utf-8")
    manager = SuiteManager(manifest_path=manifest, codex_skills_dir=codex, core_version="1.0.0", lock_path=tmp_path / "lock.json")
    monkeypatch.setattr(manager, "_activate_staged", lambda *_: (_ for _ in ()).throw(OSError("boom")))
    result = manager.install("ars", confirm=True)
    assert result.status == "activation_rolled_back"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_manager.py`

Expected: FAIL because `SuiteManager` is not implemented.

- [ ] **Step 3: Implement the manager**

`SuiteManager` accepts manifest path, Codex skills directory, lock path, core version, and optional clock/temp-root functions. `doctor()` returns `SuiteStatus` entries for each component without importing or executing skill code. `install()` requires `confirm=True`, stages a local file or directory source, checks SHA-256 and required files, checks Core/handoff compatibility, backs up the existing destination, activates with `os.replace`, writes the lock, and restores the backup on activation/lock failure. Use stable reason codes from the design document and never follow absolute required-file paths outside the staged root.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_manager.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
python scripts/auto_commit.py --message "feat(suite): add safe skill installation manager" --files polynexus/suite/manager.py tests/test_suite_manager.py
```

### Task 3: Add evidence handoff and CLI commands

**Files:**
- Create: `polynexus/suite/handoff.py`
- Create: `polynexus/cli/run_suite_service.py`
- Modify: `polynexus/cli/parser.py`
- Modify: `polynexus/__main__.py`
- Create: `tests/test_suite_handoff.py`
- Create: `tests/test_suite_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path

from polynexus.suite.handoff import build_suite_handoff


def test_handoff_references_existing_package_files_without_copying(tmp_path: Path):
    for name in ("manifest.json", "ars-writing-input.json", "result-tables.json", "writing-evidence.json", "citation-metrics.json"):
        payload = {"package_id":"demo","version":1} if name == "manifest.json" else {}
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    result = build_suite_handoff(tmp_path)
    assert result["status"] == "ready"
    assert result["files"]["ars_writing_input"] == "ars-writing-input.json"
    assert not (tmp_path / "handoff-copy.json").exists()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_handoff.py tests/test_suite_cli.py`

Expected: FAIL because the handoff and `suite` CLI route do not exist.

- [ ] **Step 3: Implement handoff and CLI delegation**

`build_suite_handoff()` must call `load_evidence_package_view()` for full package validation, return package-relative paths, package id/version/status, handoff schema, and `human_review_required`, and return `evidence_package_invalid` on validation failure. Add an argparse `suite` parser with `doctor`, `install-ars`, `update`, `rollback`, and `handoff` operations. `run_suite_service.py` prints one JSON object and delegates every operation to `SuiteManager` or `build_suite_handoff`; installation requires an explicit `--yes` flag so normal CLI use cannot silently write.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_handoff.py tests/test_suite_cli.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
python scripts/auto_commit.py --message "feat(suite): expose CLI and evidence handoff" --files polynexus/suite/handoff.py polynexus/cli/run_suite_service.py polynexus/cli/parser.py polynexus/__main__.py tests/test_suite_handoff.py tests/test_suite_cli.py
```

### Task 4: Add the GUI thin adapter and cross-entry verification

**Files:**
- Create: `polynexus/gui/suite_manager_adapter.py`
- Create: `tests/test_suite_gui_adapter.py`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-08-29-suite-runtime-installation.md`

- [ ] **Step 1: Write the failing test**

```python
from polynexus.gui.suite_manager_adapter import SuiteManagerAdapter


def test_gui_adapter_returns_same_json_safe_projection_as_service(tmp_path):
    adapter = SuiteManagerAdapter(manifest_path=tmp_path / "manifest.json", codex_skills_dir=tmp_path / "skills", lock_path=tmp_path / "lock.json")
    assert adapter.doctor().status in {"ready", "component_missing", "codex_not_found"}
```

- [ ] **Step 2: Run test and verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_gui_adapter.py`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Implement the thin adapter**

The adapter constructs the same `SuiteManager`, returns its DTO `to_dict()` projections, and exposes no technique-specific branches or Qt dependencies. It must be safe to call from a GUI settings panel later.

- [ ] **Step 4: Run cross-entry and structured verification**

Run: `python -m pytest -p no:cacheprovider -q tests/test_suite_contracts.py tests/test_suite_manager.py tests/test_suite_handoff.py tests/test_suite_cli.py tests/test_suite_gui_adapter.py`

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-29-suite-runtime-installation.md --changed --types`

Run: `git diff --check`

Expected: all focused tests and the task verifier pass; no diff whitespace errors.

- [ ] **Step 5: Record acceptance and checkpoint**

Document exact counts, compatibility limitations, and untouched pre-existing files in the acceptance note and memory. Then run:

```powershell
python scripts/auto_commit.py --message "feat(suite): complete runtime integration" --files polynexus/gui/suite_manager_adapter.py tests/test_suite_gui_adapter.py docs/agent/memory/active-work.md docs/acceptance/2026-08-29-suite-runtime-installation.md
```
