---
title: Formal pytest collection boundary for temporary diagnostics
date: 2026-07-31
status: approved
---

# Formal pytest collection boundary

## Decision

The repository's formal pytest collection excludes directories beginning with
`_tmp` through `pytest.ini`'s `norecursedirs` setting. Temporary diagnostic
tests remain available when a developer invokes their explicit path, but they
are not part of the repository-wide `pytest -q` release gate.

## Rationale

The full verifier collected an untracked `tests/_tmp_phase3` diagnostic test
whose assertion expects an obsolete repository-root output directory. The
repository contract places temporary diagnostics outside the formal source
and test surface. Excluding the directory at collection time fixes the
boundary at its source without editing, deleting, or hiding the user-owned
diagnostic file.

## Safety boundaries

- No production behavior, scientific policy, real dataset, or generated
  output is changed.
- This does not alter direct path invocation of a temporary test.
- Only directories matching `_tmp*` are excluded; ordinary canonical tests
  under `tests/` remain collected.
- The full release gate still requires complete pytest output, wrapper exit
  code `0`, and a successful boundary audit.
