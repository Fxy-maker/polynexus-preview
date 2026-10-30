# Preview failure repair — 2026-10-13

## Outcome and scope

Repairs run on `codex/research-preview-closeout-2026-10-13` in the isolated
`preview-october-closeout/PolyNexus` checkout. The original 38 failing nodes
now pass individually as one selection (`38 passed`, 21.43 seconds). No
failing assertion was skipped, and no capability was promoted.

## Product repairs

- SAXS strain tracking no longer converts a finite ensemble long-period
  fallback into a new peak when Core has recorded an explicit failed peak
  selection. Feature-dependent structure/orientation remains unavailable
  after loss; independent total-channel calculations continue.
- GUI history keeps its lightweight header query and hydrates only the selected
  or hovered row. Its existing shared row builder supplies metrics, source
  availability and scientific/diagnostic status without loading other runs.
- GUI log batches use explicit HTML paragraphs so escaped input displays
  literally, appends at the end and respects the existing 500-block bound.
- Gallery toolbars scroll at narrow widths; card layout follows viewport width
  and preserves reusable thumbnails before deleting old row containers.
- Sample filtering clears the current cell when the selected sample disappears.
  Navigation logs use the translated submodule label.
- TGA replay defaults use a dataclass factory, resolving the Python 3.11 CI
  import error for an immutable mapping default.

## Fixture corrections and their contract basis

| Old assumption | Correct regression boundary |
| --- | --- |
| Default figure output includes expensive PNG/PDF/preview assets | Tests requesting all assets explicitly use `paper_complete`; production keeps the `evidence` default |
| SAXS signed residuals are discarded | Retain finite signed observations for integral/correlation consumers, per the 2026-08-04 scientific-correctness contract |
| New strain outputs populate legacy `Q_star` fields | Assert `invariant_Q`/`invariant_Q_rel`; detached historical aliases remain inputs only |
| A peakless profile supports tracked-feature orientation | Channel-isolation fixture declares a resolvable peak and window; dedicated loss/peakless tests still reject tracked-feature outputs |
| A worker with an absent/unmappable raw file reaches a fake provider | Supply a canonical-admissible file; test translated unexpected service exceptions at that boundary |
| Headerless IR columns may be guessed | Provide explicit wavenumber/absorbance column labels |
| A generic DSC program automatically excludes its 255 °C hold | Retain and assert both observed holds; a material-independent test cannot establish a melt transition from temperature alone |
| Database row zero/one has a particular sample/run | Bind to the selected sample ID or the actual ordered snapshot |
| Orientation-advisory rejection precedes a missing mode check | Supply the declared mode so the test reaches the authority rejection it intends to verify |

The strain table regression also checks the expanded total/directional peak,
tracking, and invariant field inventory. These are existing public fields,
not a schema introduced by this repair.

## Verification

All runs use `QT_QPA_PLATFORM=offscreen`, `MPLBACKEND=Agg`, `PYTHONUTF8=1`,
and `PYTHONPATH` pointing at the isolated checkout.

- Original-node replay: `38 passed`.
- Main-window/gallery/history/IR/SAXS/figure/TGA/DSC surrounding selection:
  `541 passed`, with one intentional legacy-name contract conflict exposed;
  that conflict was corrected by retaining the canonical invariant names.
- Focused corrected invariant/default/log/history/TGA checks passed.
- Chart editor plus workflow: `305 passed`. A full run exposed one transient
  PySide6 action-connection failure during editor construction; its isolated
  rerun passed. The fixture now collects Python/scene callback cycles after
  flushing deferred Qt deletion. This mitigates lifecycle contamination;
  it is not a proven correction to Qt's native binding implementation.
- Log/startup/cached-history regressions: `8 passed`, including literal text,
  append order, and actual removal of old lines under the log bound.
- First broad gate: quality `313`, preprocessing `157`, full suite
  `4994 passed, 1 failed, 50 skipped` in 540.16 seconds. This is retained as
  investigation evidence rather than described as a passing run.
- Final full/type/boundary gate: passed. Full suite `4995 passed, 50 skipped,
  24 warnings` in 599.70 seconds; quality `313`, preprocessing `157`, cumulative
  Ruff/compile, whitespace and boundary checks passed. No failed node was
  skipped by this repair. Separate `pyright -p pyrightconfig.json` reports
  `0 errors, 0 warnings, 0 informations`.

Exact integration command:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-10-13-preview-failure-repair.md --base preview/research-preview-v0.1 --changed --types --full --boundary
```

Original-node replay uses the exact `FAILED` node IDs in the prior regression
log and invokes `python -m pytest -p no:cacheprovider -q @failedNodes --tb=short`.
Chart replay invokes `python -m pytest -p no:cacheprovider -q
tests/test_chart_editor.py tests/test_chart_editor_workflow.py --tb=short`.
Temporary logs remain under Git worktree metadata, outside tracked files.

## Human review and preservation

Concrete decisions, recommendations and source/test pointers are in
[the human-review notes](2026-10-13-preview-human-review.md). This repair does
not resolve the existing inferred DSC preparation-role semantics, provide an
OS sandbox, or certify advanced scientific models. These boundaries are
explicit for the human merge review required by AGENTS.md section 7.

The original `D:/PolyNexus` checkout, personal/untracked drafts, literature
files and `tests/_tmp_phase3/` remain untouched. Private origin/mainline, raw
datasets and other worktrees are outside the mutation scope. The existing
public PR #1 remains a draft until the human review is complete.
Its GitHub checks are the live evidence for the clean Windows/Python 3.11
environment; local full verification here used Python 3.12.

## Clean CI dependency follow-up

GitHub runs `38366433798` and `38366844398` reached the full-suite collection
after passing quality 313 and preprocessing 157, then failed importing
`tests/test_gui_automation_mcp.py` because the `mcp` package was absent. The
workflow installed only `.[dev]`; MCP is declared in the optional `automation`
extra. CI and the full-suite development instructions now install
`.[dev,automation]`. Ordinary application installation remains optional, and
no automation test is skipped or weakened.

The updated workflow regression first failed on the missing extra, then
`python -m pytest -p no:cacheprovider -q tests/test_ci_workflow.py
tests/test_gui_automation_mcp.py --tb=short` passed all 6 tests. The next clean
run exposed an API-major-version mismatch: the unconstrained install selected
MCP 2.x, while this server uses the MCP 1.x `FastMCP` API. The automation extra
now pins `mcp>=1.0,<2`; a focused rerun passes 7 tests. Final-head
Windows/Python 3.11 CI must still pass before this external failure is closed.

The following full-suite failures were then repaired on the final clean-run
surface:

- `python-docx` is now a regular project dependency because the manuscript
  builder's output contract includes `manuscript.docx`.
- Generated data-coordinate text anchors now participate in the initial axis
  data limits, preventing Matplotlib/FreeType overflow when a large valid
  coordinate is first rendered on a linear axis and later switched to log.
- The symlink provenance test now asserts the existing security contract:
  symlink/reparse-point raw inputs return `needs_input` before the provider;
  the Core does not follow them into a different source identity.

The focused replacement set passes 8 tests. These changes preserve the
existing `needs_input` behavior for genuinely unreadable or unmappable data.
