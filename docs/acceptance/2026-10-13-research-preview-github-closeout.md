# Research-preview GitHub integration evidence

Date: 2026-10-13

## Scope

Target: `Fxy-maker/polynexus-preview`, base `research-preview-v0.1` at
`f63b35860fff6eea602c14fbb13b0ff937b4991a`.
Completed source HEAD: `2e4aefd7e50ea96e571afec7d22dce5068e29ae5`.
The incoming scope is 50 commits / 182 files before closeout repairs.

- Sample-neutral TGA, DMA, rheology, SEC/GPC, and mechanics routes, explicit
  diagnostic model specs, uncertainty projections, shared figures/exports.
- Bounded ODS, observed TA DMA, and observed Netzsch DSC/TGA readers.
- Portable export bindings across GUI, CLI, Agent, series, and project routes.
- Canonical-bound exploration, limited worker execution, evidence curation,
  promotion-readiness records, and public replay/validation aggregation.

The proposed ReferenceEvidence changes are outside this PR. No reference
values for unknown materials are inferred or added.

## Closeout repairs

- CI now listens on the actual public preview base, alongside `main`.
- README and open-source guidance describe implemented diagnostic models and
  explicit SEC calibration rather than obsolete unsupported-only statements.
- Cumulative Ruff checks exposed 32 existing style errors in the changed
  engine module. Expanded one-line statements and retained explicit registry
  re-exports; numerical behavior is unchanged.
- The isolated public checkout exposed three collection failures caused by
  absent optional local datasets. The real walkthrough now reports missing
  local data as a module skip; SAXS discovery accepts an absent fixture root.
  Existing real-data assertions still run when their fixtures are present.
- NMR registry checks use an independent existing test file; four vendor
  replays skip when their optional inputs are absent. Joint replay checks
  fixture availability before asserting fixture identity. Generated phase-3
  Chroma scratch databases are ignored and excluded from the checkpoint.
- Updated CI branch, CLI short-signature reason, validation-directory, and
  artifact-tampering regressions to the actual shared contracts. Tampered
  artifact rejection is exercised both with input inspection and without it.

## Verification

The full command is recorded in the linked task card. Initial passes reached
Ruff/compile, the core quality gate (`313 passed`), and preprocessing
(`157 passed`), before identifying the real-data collection errors. The focused
collection regression now reports `3 skipped` instead of `3 errors`.

- `pyright -p pyrightconfig.json`: 0 errors, 0 warnings, 0 informations.
- `python scripts/boundary_audit.py --root . --json`: exit 0; structural
  inventory only, not a scientific sign-off.
- `git diff --check preview/research-preview-v0.1`: passed after style repair.
- Cumulative full-suite run: `49 failed, 4948 passed, 45 skipped, 25 warnings`
  in 547.57 seconds. This gate failed; no full-suite green claim is made.
- Published-baseline comparison: 48 of those cases exist in `f63b3586`;
  `44 failed, 4 passed` in 15.43 seconds on that unchanged checkout.
- After closeout repairs, replaying the original failure selection reports
  `38 failed, 7 passed, 5 skipped` in 12.88 seconds. All 38 remaining failures
  also failed on the published baseline. This is a targeted repair check,
  not a second complete full-suite run.
- Focused closeout contract/NMR checks: `62 passed, 4 skipped`.
- Completed-module regression selection: `438 passed, 3 skipped` in
  64.41 seconds. This covers all Python test files changed by the 50 completed
  commits relative to the public base.
- Final structured gate without repeating the known failing full suite:
  task/memory validation, cumulative Ruff/compile, core quality (`313 passed`),
  preprocessing (`157 passed`), whitespace, and boundary inventory passed.

Exact additional verification commands (PowerShell):

```powershell
$tests = @(git diff --name-only preview/research-preview-v0.1 HEAD -- tests | Where-Object { $_ -match '^tests/.+\.py$' })
python -m pytest -p no:cacheprovider -q @tests --tb=short
python -m pytest -p no:cacheprovider -q tests/test_ci_workflow.py tests/test_cli_run_single_service.py tests/test_project_workflow_workspace.py tests/test_project_workflow_package.py tests/eval/test_nmr_vendor_real_case_registry.py --tb=short
python scripts/verify.py --task docs/agent/tasks/2026-10-13-research-preview-github-closeout.md --base preview/research-preview-v0.1 --changed --types --boundary
```

All pytest/verification runs set `QT_QPA_PLATFORM=offscreen`, `MPLBACKEND=Agg`,
`PYTHONUTF8=1`, and `PYTHONPATH` to the actual isolated checkout. Failure
replays used the exact node IDs from the initial full-suite summary on both
the completed checkout and the unchanged public baseline.

## Remaining baseline failures

These failures are not silently skipped or reclassified as passing. Their
scientific and GUI fixes require separately scoped tasks; the integration PR
remains a draft pending review and a decision on the existing baseline.

| Boundary | Failures | Observed problem |
| --- | ---: | --- |
| Main-window history/workspace tests | 14 | Labels, status/table projections, tooltips, and worker fixture expectations |
| Gallery layout | 1 | Offscreen card reflow assertion |
| Sample-browser interactions | 3 | Selection and clipboard behavior |
| Cross-technique/editor/detector figure tests | 5 | Expected export roles/assets differ from emitted profiles |
| IR bridge | 1 | Canonical conversion reports ambiguous column mapping |
| SAXS mask/advisory/numerical/feature-tracking tests | 12 | Worker fixture, sanitization, mode rejection, source channel, tracking loss, and model-call compatibility |
| SAXS table template | 1 | Expected strain field inventory differs |
| DSC golden workflow | 1 | Expected isothermal segment coordinate differs from emitted coordinate |
| Total | 38 | All reproduced on the published baseline |

## Publication inventory

The 50 incoming commits contain no matching high-confidence GitHub token,
OpenAI project key, or private-key header patterns. This is a targeted scan,
not a claim that every possible secret format was audited. No incoming blob
exceeds 1 MiB, and the newly added file inventory contains no raw archives,
experimental tables, generated paper/evidence assets, or local databases.
Downloaded validation archives remain external to Git.

## Review and capability boundary

All new advanced model outputs remain diagnostic. Deterministic double replay
does not establish numerical accuracy, certified standards, uncertainty
validity, or capability promotion. Cross-file joint fits require an explicit
grouped canonical experiment. The Python worker supplies process separation
and bounded policy checks; it is not OS-enforced isolation for hostile code,
especially for Windows resource limits. Human architecture/scientific review
is required before merge under AGENTS.md section 7.

## Workspace preservation

Work uses the managed `preview-october-closeout` checkout. The original
`D:/PolyNexus` branch and all personal plans/specs, `li2020.txt`, `lotz2021.txt`,
and `tests/_tmp_phase3/` remain untouched. No local `main` or private-origin
branch integration is part of this task.

Task: [Research-preview closeout](../agent/tasks/2026-10-13-research-preview-github-closeout.md).
