# PolyNexus Windows CI Quality Gate Design

**Date:** 2026-07-10

**Status:** Proposed for implementation review

## Context

PR #4 introduces the unified figure artifact lifecycle. Its local audit passes the complete
repository suite, but the repository has no checked-in GitHub Actions workflow. GitHub therefore
reports no automated checks for the pull request.

The repository is private, GitHub Actions is enabled, and workflow permissions default to
read-only. The current GitHub plan does not expose branch protection for this private repository:
the branch-protection API returns `403` with the requirement to upgrade to GitHub Pro or make the
repository public. The repository's default branch is currently
`codex/phase2-unified-editor`, while PR #4 targets `main`.

The local Windows baseline for the intended CI command is:

- command: `python scripts/quality_gate.py --all-tests`
- focused gate: `260 passed`
- complete suite: `1563 passed`, `19 skipped`, `4 warnings`, `0 failed`
- total command time: 439.4 seconds
- lifecycle boundary scan: passed before subprocess checks began

## Goals

1. Add one authoritative Windows GitHub Actions check for pull requests targeting `main` and
   pushes to `main`.
2. Install the project and its declared development dependencies in a clean Python environment.
3. Run the existing repository-owned quality gate with the complete test suite.
4. Preserve the unified figure lifecycle boundary scan as part of the same required process.
5. Produce a stable check name that can become a technically required status check if branch
   protection later becomes available.
6. Verify the workflow locally, push it to PR #4, and confirm a successful GitHub Actions run for
   the pushed head commit.

## Non-goals

- Do not make the repository public.
- Do not change the repository default branch.
- Do not upgrade or purchase a GitHub plan.
- Do not merge PR #4.
- Do not add Linux or Python-version matrix coverage in this first CI baseline.
- Do not require unavailable external IR or NMR instrument fixtures.
- Do not duplicate the lifecycle boundary rules inside YAML.

## Chosen Approach

Use one Windows job named `CI / windows-quality-gate`. A single job avoids installing the large
scientific and GUI dependency stack more than once and makes the merge decision unambiguous. The
job delegates all repository-specific validation to
`python scripts/quality_gate.py --all-tests`, which already performs the lifecycle AST scan,
compilation, focused maintenance tests, the complete pytest suite, and the whitespace check in a
fail-fast sequence.

The alternatives were rejected for the initial baseline:

- Separate quality and full-test jobs would duplicate dependency installation and repeat focused
  tests without adding coverage.
- A Python 3.10/3.11 matrix would double cost and failure surface before the repository has a
  stable single-platform CI baseline.

## Workflow Contract

Create `.github/workflows/ci.yml` with these invariants:

- workflow name: `PolyNexus CI`
- events:
  - `pull_request` with base branch `main`
  - `push` to branch `main`
- permissions: `contents: read`
- concurrency: one run per workflow and ref, with an older run cancelled after a newer commit
- runner: `windows-latest`
- job display name: `CI / windows-quality-gate`
- job timeout: 45 minutes
- environment:
  - `QT_QPA_PLATFORM=offscreen`
  - `MPLBACKEND=Agg`
  - `PYTHONUTF8=1`
- checkout: `actions/checkout@v4`
- Python: `actions/setup-python@v5` with Python `3.11` and pip caching keyed by `pyproject.toml`
- installation:
  - `python -m pip install --upgrade pip`
  - `python -m pip install -e ".[dev]"`
- verification: `python scripts/quality_gate.py --all-tests`

No repository or organization secrets are required. Dependency or test failures fail the job;
there is no permissive fallback and no `continue-on-error` path.

## Lifecycle Boundary Coverage

The workflow must call the quality-gate entry point rather than reproduce its commands. At startup,
`scripts/quality_gate.py` calls `scan_figure_lifecycle_sources(root)`. Any violation returns exit
code 1 before compile or pytest subprocesses run. This keeps the ownership rules for providers,
export formats, recursive gallery discovery, and manifest-backed editor capabilities in one
versioned Python implementation with existing unit coverage.

## Test Strategy

Implementation follows a red-green sequence:

1. Add `tests/test_ci_workflow.py` before the workflow exists.
2. Assert that the workflow file exists and contains the agreed triggers, permissions, runner,
   Python version, cache, headless GUI environment, timeout, and exact quality-gate command.
3. Run the new test and confirm it fails because `.github/workflows/ci.yml` is missing.
4. Add the minimal workflow and confirm the contract test passes.
5. Run `python scripts/quality_gate.py --all-tests` locally.
6. Confirm `git diff --check` and a clean expected worktree state.
7. Commit and push the branch.
8. Use the GitHub API to confirm that the workflow is accepted, that the PR #4 head SHA matches
   the pushed commit, and that its Windows job completes with conclusion `success`.

The contract test uses only Python's standard library and pytest. GitHub's accepted workflow run
is the authoritative remote YAML and runner validation.

## Gate Semantics and Current Plan Limitation

On the current private-repository plan, the green check is a process gate: PR #4 must not be merged
until `CI / windows-quality-gate` succeeds for its current head SHA. GitHub cannot technically
disable the merge button without branch protection. This limitation must remain explicit in the
PR description and completion report.

If the account later gains private-repository branch protection, configure the already stable
`CI / windows-quality-gate` context as a required status check. That future repository-setting
change does not require renaming or redesigning the workflow.

## Acceptance Criteria

The CI baseline is complete only when all of the following are evidenced:

1. `.github/workflows/ci.yml` satisfies the workflow contract.
2. The workflow contract test has a recorded red failure and subsequent green pass.
3. The complete local quality gate exits 0 on the final committed content.
4. The CI commit is pushed to `codex/unified-figure-lifecycle-foundation`.
5. PR #4 points at that exact head SHA.
6. GitHub reports the corresponding Windows workflow run and job conclusion as `success`.
7. The completion report states that branch-protection enforcement remains unavailable on the
   current private-repository plan.
