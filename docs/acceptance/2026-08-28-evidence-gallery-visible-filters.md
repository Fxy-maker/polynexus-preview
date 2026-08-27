# Evidence gallery visible filters — 2026-08-28

The evidence package dialog now exposes technique and group selectors derived
from the immutable `figure_views` index. Changes reload the existing read-only
`ChartGallery` through `EvidencePackageViewAdapter`; role/category/search
controls remain available and no figure assets are deleted.

Verification:

- `python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_plot_gallery_service.py` — **25 passed**.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-28-evidence-gallery-visible-filters.md --changed --types` — selected checks passed; quality gates **310 + 157 passed**.
- `git diff --check` — passed through the quality gate.

Full repository release status remains governed by the existing historical
GUI/chart/SAXS failure ledger.
