# NMR real-data lifecycle closure acceptance

## Delivered

All four NMR partitions now have one real-data lifecycle regression:

- liquid 1H: `液体核磁/H谱`
- liquid 13C: `液体核磁/C谱`
- solid 1H: `固体nmr氢谱`
- solid 13C: `固体nmr碳谱`

Each partition runs through `NMREngine.run_pipeline`, shared evidence,
Manifest/Gallery, Main editor working save and publication, export figure-run
provenance, and MainWindow History restore. Outputs are written only to pytest
temporary roots; repository fixtures and their existing generated outputs are
untouched. Solid 13C assignment-limited Xc remains provisional.

## Verification evidence

```text
python -m pytest tests/test_nmr_lifecycle_closure.py -q
4 passed in 252.98s (0:04:12)

python -m pytest <NMR lifecycle/engine/provider/provenance/eval/export/history matrix> -q
47 passed in 348.63s (0:05:48)
```

## Remaining acceptance boundary

Restarted-GUI visual review, human scientific sign-off, and the shared AI-off/
failure/fallback release matrix remain open. The real-data evidence here is
automated and does not promote assignment-limited solid-state conclusions.
