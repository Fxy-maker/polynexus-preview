# PolyNexus Full Software Release Audit

Date: 2026-07-27
Branch: `codex/origin-editor-usable-controls`
Status: automated evidence in progress; release not approved

## Evidence ledger

| Boundary | Current evidence | Classification |
| --- | --- | --- |
| WAXS publication cutover and provider/workbench contracts | `30 passed` from the dedicated publication matrix with isolated basetemp | automated-pass |
| Cross-technique AI-off/failure/fallback | `25 passed` across DSC, IR, WAXS, SAXS, and NMR; Joint is explicitly report-level | automated-pass |
| Canonical GUI default shell | Restarted canonical window screenshot shows SAXS empty state, workspace summary, mode navigation, and Data/Config/Results/Plots shell | human-review |
| Combined lifecycle/real-fixture slice | 180-second tool window expired without a summary; no pass or failure inferred | bounded-timeout |
| Full repository verifier | Previous fresh run reached `2763 passed, 1 failed, 10 warnings`; WAXS publication test failed and boundary did not run | limitation; fresh rerun pending |

## Automated commands and results

### WAXS publication recheck

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_waxs_pub_matrix'
python -m pytest -q tests/test_waxs_publication_cutover.py tests/test_waxs_publication_temperature_provider.py tests/test_waxs_publication_strain_provider.py tests/test_waxs_publication_static_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_waxs_figure_provider.py tests/test_waxs_figure_document.py
```

Result: `30 passed in 3.49s`.

### AI safety matrix

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_ai2'
python -m pytest -q tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py -vv
```

Result: `25 passed in 0.68s`. This proves the contract boundary only; it does
not prove real model quality, candidate calibration, or human scientific
approval.

### Combined lifecycle attempt

The combined command containing the real walkthrough, all five technique
lifecycle closures, IR mapping, NMR/Joint provenance, and WAXS publication
cutover exceeded the 180-second tool limit without a test summary. The running
pytest process was explicitly identified and terminated after the timeout.
This result is recorded as `bounded-timeout`, not as pass or failure.

## GUI evidence

The canonical GUI was inspected from `D:\PolyNexus`. The temporary screenshot
is:

`C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-gui-default.png`

Observed: the main window opens on the SAXS empty state, shows `No project`,
workspace/run status, SAXS static/temperature/strain navigation, and the
Data/Config/Results/Plots shell. This is visual evidence for a reviewer. A
complete restarted-GUI walkthrough of all modes, Gallery, Editor, Export, and
History is still open.

## Open release gates

- Run the real/lifecycle shards one at a time with dedicated basetemps.
- Re-run `scripts/verify.py --changed --types --full --boundary` with a
  dedicated basetemp and preserve any exact failure/timeout.
- Complete restarted-GUI visual review for all requested routes.
- Review IR vendor-native mapping/ROI semantics.
- Review assignment-limited solid-state NMR and Joint scientific conflicts.
- Complete the human scientific publication decision and final AI-off/
  failure/fallback release approval.

No code change in this audit promotes a diagnostic-only result or changes a
scientific threshold.
