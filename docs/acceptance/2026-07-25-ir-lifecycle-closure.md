# IR figure lifecycle closure acceptance

## Delivered

IR standard, temperature-2D, and mapping/ROI now have one automated lifecycle
regression using the existing typed DTO providers. Each mode publishes a
Manifest-backed run, verifies active Gallery roles and run context, saves and
publishes a working figure revision, exports `metadata/runs` plus the active
pointer, and restores the same Gallery through MainWindow History.

The mapping case additionally asserts that `recipe.provenance.source_id` and
the invalid-pixel diagnostic count survive publication. No vendor reader,
coordinate inference, or band-meaning policy was introduced.

## Verification evidence

```text
python -m pytest tests/test_ir_lifecycle_closure.py -q
3 passed in 17.18s

python -m pytest <IR lifecycle/provider/temperature/mapping/export/history matrix> -q
47 passed in 33.07s
```

## Remaining acceptance boundary

Vendor-native mapping input semantics, real/Golden IR source acceptance,
restarted-GUI visual review, and the shared AI-off/failure/fallback scientific
release matrix remain open. The normal Gallery remains manifest-only and legacy
`Fig-IRT*` discovery is not promoted.
