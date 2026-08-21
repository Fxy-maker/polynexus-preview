# Evidence Figure Role Projection Acceptance

Date: 2026-08-21

## Delivered behavior

`figure-index.json` no longer labels every packaged figure as `diagnostic`
with the package's first evidence technique.  The packager now carries bounded
source metadata through its existing asset descriptors:

- a `FigureCandidateSet.main_candidates` SVG is `manuscript_candidate`;
- a `supporting_candidates` SVG is `supporting_candidate`;
- unselected run output remains `diagnostic`;
- the index technique comes from the producing run or explicitly declared
  candidate technique;
- selected group figures keep their single explicit group ID;
- all such entries remain `review_only` until human review.

Candidate PNG/SVG siblings remain one logical SVG entry. Different candidates
in the same renderer output directory remain distinct by their figure stem,
while a role, technique, or group conflict for the same logical figure fails
package construction rather than silently promoting or demoting it. A
candidate lacking an SVG also fails rather than producing an unindexed PNG/PDF
asset.

## Verification

The regression test was first observed failing on the old literal projection:

```text
expected: manuscript_candidate / IR / ir:pa6-jw:temperature_C
actual:   diagnostic / DSC / null
```

After the repair, the shared producer/consumer matrix passed:

```text
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py tests/test_plot_gallery_service.py
64 passed in 7.05s
```

`ruff check polynexus/core/project_workflow/package.py
tests/test_project_workflow_package.py`, `python -m compileall -q
polynexus/core/project_workflow/package.py`, and `git diff --check` passed.

## Read-only PA6 replay

The existing PA6 FTIR group was selected through the normal CLI:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv `
  --question "Describe PA6 JW FTIR evolution" `
  --package-id pa6-role-projection-smoke `
  --figure-selection <selection-json>
```

The fresh package
`D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\pa6-role-projection-smoke-v002`
has 19 index entries: 18 `diagnostic` IR run figures and one selected group
overlay:

```json
{
  "role": "manuscript_candidate",
  "technique": "IR",
  "group": "ir:pa6-jw:temperature_C",
  "writing_eligibility": "review_only",
  "svg": "figures/ftir_group_overlay.svg"
}
```

The selected overlay contains its SVG and metadata sidecar, with no PNG sibling. The
underlying external raw data remained read-only; the package remains
`review_required`, and no scientific or publication claim was promoted.

## Limitation

This fixes candidate-role projection, not candidate generation. FTIR currently
has the ARS group renderer; DSC, SAXS, WAXS, and NMR require their own selected
group-figure protocols before they can produce comparable candidate entries.
