---
task_id: YYYY-MM-DD-short-topic
kind: daily | architecture | schema | security | performance | scientific
status: proposed | active | implementation_complete_review_required | complete
date: YYYY-MM-DD
title: Short action-oriented title
---

# Task Title

## Goal

One observable outcome.

## Non-goals

- Explicitly excluded behavior or boundary.

## Shared objects and entry points

- Objects: project | run | chart | evidence package | export
- AI/Codex/CLI: unchanged | reads | creates | updates | exports
- GUI: unchanged | reads | creates | updates | exports
- Cross-entry rule: name the producer and every changed consumer. If all are
  unchanged, say why this task is isolated.

## Acceptance criteria

- [ ] Observable behavior and failure behavior.
- [ ] Provenance, scientific boundary, or human-review condition when relevant.
- [ ] Cross-entry consistency condition for every shared object changed.

## Verification

```powershell
# Focused tests only; set POLYNEXUS_TEST_RETENTION=review or evidence only when needed.
python -m pytest -p no:cacheprovider -q tests/path/to/focused_test.py
python scripts/verify.py --task docs/agent/tasks/YYYY-MM-DD-short-topic.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "type(scope): short summary" `
  --files path/to/source.py tests/path/to/focused_test.py docs/agent/tasks/YYYY-MM-DD-short-topic.md
```

## Completion evidence

- Exact commands and outcomes:
- Known limitations or follow-up:
- Pre-existing changes left untouched:
