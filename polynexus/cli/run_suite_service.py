"""CLI dispatcher for the shared PolyNexus Suite Manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from polynexus.suite.handoff import build_suite_handoff
from polynexus.suite.paper_source import build_manuscript_source
from polynexus.suite.manager import SuiteManager


def run_suite(args: Any) -> int:
    manager = SuiteManager(
        manifest_path=getattr(args, "manifest", None),
        codex_skills_dir=getattr(args, "codex_skills_dir", None),
        lock_path=getattr(args, "lock", None),
    )
    operation = str(args.operation)
    if operation == "manuscript-source":
        package = getattr(args, "package", None)
        output = getattr(args, "output", None)
        if not package or not output:
            payload = {"status": "blocked", "reason_codes": ["package_and_output_required"]}
        else:
            try:
                brief = None
                if getattr(args, "brief", None):
                    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
                source = build_manuscript_source(Path(package), brief)
                destination = Path(output).expanduser().resolve()
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(f".{destination.name}.tmp")
                temporary.write_text(json.dumps(source.to_dict(), ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
                temporary.replace(destination)
                payload = {"status": "ready", "source": {"path": str(destination), **source.to_dict()}}
            except (OSError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
                payload = {"status": "blocked", "reason_codes": ["manuscript_source_invalid"], "error": str(exc)}
    elif operation == "handoff":
        payload = build_suite_handoff(Path(args.package))
    elif operation == "doctor":
        payload = manager.doctor().to_dict()
    elif operation == "install-ars":
        payload = manager.install("ars", confirm=bool(getattr(args, "yes", False)), source_override=getattr(args, "source", None)).to_dict()
    elif operation == "update":
        payload = manager.update(getattr(args, "component", None), confirm=bool(getattr(args, "yes", False))).to_dict()
    elif operation == "rollback":
        payload = manager.rollback(getattr(args, "component", None)).to_dict()
    else:
        payload = {"status": "failed", "reason_codes": ["operation_unknown"]}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"ready", "installed", "rolled_back", "confirmation_required", "component_missing", "codex_not_found"} else 1


__all__ = ["run_suite"]
